"""Twin-to-twin async handshake pipeline with strict validation.

The pipeline emits three deterministic envelope types:
1) Intake-to-Architecture Packet
2) Architecture-to-Risk Packet
3) Risk-to-Build Execution Packet
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Generic, Literal, TypeVar

from .exceptions import CriticalMisalignmentError, PipelineHaltException, QuorumDissentException
from .fault import dump_critical_misalignment
from .governance import GovernanceLogger
from .hashutil import fnv1a_32
from .quorum import ValidationQuorumManager
from .recovery import CheckpointManager, CheckpointSnapshot, execution_token
from .schema import Schema, SchemaValidationError, signature_for, validate_against_schema
from .transaction_manager import WorkspaceTransaction, cleanup_workspace_staging, ensure_workspace_io_hooks_installed
from .types import JSONObject
from .validator import SchemaValidator
from .sandbox import AgentSandboxExecutor

T = TypeVar("T", bound=JSONObject)

SequenceName = Literal[
    "intake_to_architecture",
    "architecture_to_risk",
    "risk_to_build_execution",
]


@dataclass(frozen=True, slots=True)
class PacketEnvelope(Generic[T]):
    sequence: SequenceName
    schema_id: str
    payload: T
    signature: str
    source_role: str
    correlation_id: str
    created_at: float


def handshake_schemas() -> dict[str, Schema]:
    intake_to_architecture: JSONObject = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "business_case",
            "target_repositories",
            "requirements",
            "workspace_snapshot",
        ],
        "properties": {
            "business_case": {"type": "string"},
            "target_repositories": {"type": "array", "items": {"type": "string"}},
            "requirements": {"type": "array", "items": {"type": "string"}},
            "workspace_snapshot": {"type": "object", "additionalProperties": True, "required": []},
        },
    }

    architecture_to_risk: JSONObject = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "target_repositories",
            "architecture_plan",
            "impact_assessment",
            "trace",
        ],
        "properties": {
            "target_repositories": {"type": "array", "items": {"type": "string"}},
            "architecture_plan": {"type": "array", "items": {"type": "string"}},
            "impact_assessment": {"type": "object", "additionalProperties": True, "required": []},
            "trace": {
                "type": "object",
                "additionalProperties": False,
                "required": ["intake_signature"],
                "properties": {"intake_signature": {"type": "string"}},
            },
        },
    }

    risk_to_build_execution: JSONObject = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "target_repositories",
            "compliance_status",
            "risk_summary",
            "recommended_actions",
            "trace",
        ],
        "properties": {
            "target_repositories": {"type": "array", "items": {"type": "string"}},
            "compliance_status": {"type": "string"},
            "risk_summary": {"type": "array", "items": {"type": "string"}},
            "recommended_actions": {"type": "array", "items": {"type": "string"}},
            "trace": {
                "type": "object",
                "additionalProperties": False,
                "required": ["architecture_signature"],
                "properties": {"architecture_signature": {"type": "string"}},
            },
        },
    }

    return {
        "intake_to_architecture.v1": Schema("intake_to_architecture.v1", intake_to_architecture),
        "architecture_to_risk.v1": Schema("architecture_to_risk.v1", architecture_to_risk),
        "risk_to_build_execution.v1": Schema("risk_to_build_execution.v1", risk_to_build_execution),
    }


@dataclass(slots=True)
class HandshakeEngine:
    governance: GovernanceLogger
    schemas: dict[str, Schema]

    def create_envelope(
        self,
        *,
        sequence: SequenceName,
        schema_id: str,
        payload: JSONObject,
        source_role: str,
        correlation_id: str | None = None,
    ) -> PacketEnvelope[JSONObject]:
        schema = self._require_schema(schema_id)
        self._validate_payload(schema, payload, sequence=sequence, source_role=source_role)
        sig = signature_for(schema, payload)
        env = PacketEnvelope(
            sequence=sequence,
            schema_id=schema_id,
            payload=payload,
            signature=sig,
            source_role=source_role,
            correlation_id=correlation_id or str(uuid.uuid4()),
            created_at=time.time(),
        )
        self.governance.emit_event(
            {
                "event": "HANDSHAKE_ENVELOPE_CREATED",
                "sequence": sequence,
                "schema_id": schema_id,
                "signature": sig,
                "source_role": source_role,
                "correlation_id": env.correlation_id,
            }
        )
        return env

    def validate_envelope(self, env: PacketEnvelope[JSONObject], *, expected_sequence: SequenceName) -> None:
        if env.sequence != expected_sequence:
            raise CriticalMisalignmentError(
                f"Envelope sequence mismatch: expected {expected_sequence}, got {env.sequence}"
            )
        schema = self._require_schema(env.schema_id)
        self._validate_payload(schema, env.payload, sequence=env.sequence, source_role=env.source_role)
        expected_sig = signature_for(schema, env.payload)
        if env.signature != expected_sig:
            self.governance.emit_event(
                {
                    "event": "HANDSHAKE_SIGNATURE_INVALID",
                    "sequence": env.sequence,
                    "schema_id": env.schema_id,
                    "expected_signature": expected_sig,
                    "actual_signature": env.signature,
                    "source_role": env.source_role,
                    "correlation_id": env.correlation_id,
                }
            )
            raise CriticalMisalignmentError("Handshake signature validation failed.")
        self.governance.emit_event(
            {
                "event": "HANDSHAKE_SIGNATURE_VALID",
                "sequence": env.sequence,
                "schema_id": env.schema_id,
                "signature": env.signature,
                "source_role": env.source_role,
                "correlation_id": env.correlation_id,
            }
        )

    def _require_schema(self, schema_id: str) -> Schema:
        schema = self.schemas.get(schema_id)
        if schema is None:
            raise CriticalMisalignmentError(f"Unknown schema_id: {schema_id}")
        return schema

    def _validate_payload(
        self,
        schema: Schema,
        payload: Any,
        *,
        sequence: SequenceName,
        source_role: str,
    ) -> None:
        if not isinstance(payload, dict):
            raise CriticalMisalignmentError("Payload must be an object.")
        try:
            validate_against_schema(payload, schema.definition)
        except SchemaValidationError as exc:
            self.governance.emit_event(
                {
                    "event": "HANDSHAKE_PAYLOAD_SCHEMA_ERROR",
                    "sequence": sequence,
                    "schema_id": schema.schema_id,
                    "error": str(exc),
                    "source_role": source_role,
                }
            )
            raise CriticalMisalignmentError(str(exc)) from exc


class _Stop:
    pass


STOP = _Stop()


async def run_three_stage_pipeline(
    *,
    governance: GovernanceLogger,
    intake_agent: Any,
    architect_agent: Any,
    risk_agent: Any,
    build_agent: Any,
    business_case: str,
    workspace_snapshot: JSONObject,
    checkpoint: CheckpointManager | None = None,
    resume: CheckpointSnapshot | None = None,
    quorum: ValidationQuorumManager | None = None,
) -> JSONObject:
    ensure_workspace_io_hooks_installed()
    engine = HandshakeEngine(governance=governance, schemas=handshake_schemas())
    ledger = governance.proof_ledger

    repo_root_raw = workspace_snapshot.get("repo_root")
    repo_root = Path(repo_root_raw).resolve() if isinstance(repo_root_raw, str) else Path.cwd().resolve()
    token = checkpoint.token if checkpoint is not None else execution_token(business_case=business_case)
    cleanup_workspace_staging(repo_root=repo_root, token=token, active_stage=resume.active_stage if resume else None)

    quorum_mgr = quorum or ValidationQuorumManager(logs_dir=governance.root, proof_ledger=ledger)

    stage_to_next_role: dict[str, str] = {
        "intake_to_architecture": "software_architect",
        "architecture_to_risk": "risk_compliance",
        "risk_to_build_execution": "build_orchestrator",
    }

    def _handshake_hash(*, from_role: str, to_role: str, schema_id: str, payload: JSONObject) -> str:
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return fnv1a_32(f"{from_role}->{to_role}:{schema_id}:{canonical}")

    q1: asyncio.Queue[PacketEnvelope[JSONObject] | _Stop] = asyncio.Queue(maxsize=1)
    q2: asyncio.Queue[PacketEnvelope[JSONObject] | _Stop] = asyncio.Queue(maxsize=1)
    q3: asyncio.Queue[PacketEnvelope[JSONObject] | _Stop] = asyncio.Queue(maxsize=1)

    def _env_meta(item: PacketEnvelope[JSONObject] | _Stop) -> JSONObject:
        if item is STOP:
            return {"stop": True}
        return {
            "sequence": item.sequence,
            "schema_id": item.schema_id,
            "signature": item.signature,
            "source_role": item.source_role,
            "correlation_id": item.correlation_id,
        }

    async def _q_put(
        name: str,
        q: asyncio.Queue[PacketEnvelope[JSONObject] | _Stop],
        item: PacketEnvelope[JSONObject] | _Stop,
    ) -> None:
        if ledger is not None:
            try:
                ledger.append_block({"kind": "QUEUE_PUT", "queue": name, "item": _env_meta(item)})
            except Exception:
                pass
        await q.put(item)

    async def _q_get(
        name: str,
        q: asyncio.Queue[PacketEnvelope[JSONObject] | _Stop],
    ) -> PacketEnvelope[JSONObject] | _Stop:
        item = await q.get()
        if ledger is not None:
            try:
                ledger.append_block({"kind": "QUEUE_GET", "queue": name, "item": _env_meta(item)})
            except Exception:
                pass
        return item

    seed_stop: asyncio.Queue[PacketEnvelope[JSONObject] | _Stop] | None = None
    if resume is not None:
        next_role = stage_to_next_role.get(resume.active_stage, "unknown")
        schema = engine.schemas.get(resume.schema_id)
        if schema is None:
            raise CriticalMisalignmentError(f"Unknown schema_id in resume snapshot: {resume.schema_id}")
        hh = _handshake_hash(
            from_role=resume.source_role,
            to_role=next_role,
            schema_id=schema.schema_id,
            payload=resume.payload,
        )
        ballots = await quorum_mgr.validate(
            stage=resume.active_stage,
            schema=schema,
            payload=resume.payload,
            envelope_signature=resume.envelope_signature,
            handshake_hash=hh,
            source_role=resume.source_role,
            next_role=next_role,
            correlation_id=resume.correlation_id,
            repo_root=repo_root,
        )
        if checkpoint is not None:
            checkpoint.record_stage(
                stage=resume.active_stage,
                schema=schema,
                payload=resume.payload,
                envelope_signature=resume.envelope_signature,
                source_role=resume.source_role,
                correlation_id=resume.correlation_id,
                created_at=resume.created_at,
                next_role=next_role,
                governance_state=governance.state,
                envelope_ballots=ballots,
            )
        env = PacketEnvelope(
            sequence=resume.active_stage,
            schema_id=resume.schema_id,
            payload=resume.payload,
            signature=resume.envelope_signature,
            source_role=resume.source_role,
            correlation_id=resume.correlation_id,
            created_at=resume.created_at,
        )
        if env.sequence == "intake_to_architecture":
            await _q_put("q1", q1, env)
            seed_stop = q1
        elif env.sequence == "architecture_to_risk":
            await _q_put("q2", q2, env)
            seed_stop = q2
        elif env.sequence == "risk_to_build_execution":
            await _q_put("q3", q3, env)
        else:
            raise CriticalMisalignmentError(f"Unsupported resume stage: {env.sequence}")

    stage_timeout_s = 10.0

    async def intake_task() -> None:
        exclude = [governance.root]
        async with WorkspaceTransaction(
            repo_roots=[repo_root],
            token=token,
            stage="intake_to_architecture",
            exclude_roots=exclude,
            proof_ledger=ledger,
        ) as tx:
            payload = await sandbox.run(
                "intake_specialist.build_intake_payload",
                intake_agent.build_intake_payload,
                fn_kwargs={"business_case": business_case, "workspace_snapshot": workspace_snapshot},
                timeout_s=stage_timeout_s,
                mode="thread",
            )
            env = engine.create_envelope(
                sequence="intake_to_architecture",
                schema_id="intake_to_architecture.v1",
                payload=payload,
                source_role="intake_specialist",
            )
            next_role = stage_to_next_role["intake_to_architecture"]
            hh = _handshake_hash(from_role=env.source_role, to_role=next_role, schema_id=env.schema_id, payload=env.payload)
            try:
                ballots = await quorum_mgr.validate(
                    stage=env.sequence,
                    schema=engine.schemas[env.schema_id],
                    payload=env.payload,
                    envelope_signature=env.signature,
                    handshake_hash=hh,
                    source_role=env.source_role,
                    next_role=next_role,
                    correlation_id=env.correlation_id,
                    repo_root=repo_root,
                )
            except QuorumDissentException as exc:
                if checkpoint is not None:
                    schema = engine.schemas.get(env.schema_id)
                    if schema is not None:
                        checkpoint.record_quorum_halt(
                            stage=env.sequence,
                            schema=schema,
                            payload=env.payload,
                            envelope_signature=env.signature,
                            source_role=env.source_role,
                            correlation_id=env.correlation_id,
                            created_at=env.created_at,
                            next_role=next_role,
                            envelope_ballots=(exc.ballots if isinstance(exc.ballots, dict) else {}),
                        )
                raise
            checkpoint_ok = True
            if checkpoint is not None:
                schema = engine.schemas.get(env.schema_id)
                if schema is not None:
                    checkpoint_ok = checkpoint.record_stage(
                        stage=env.sequence,
                        schema=schema,
                        payload=env.payload,
                        envelope_signature=env.signature,
                        source_role=env.source_role,
                        correlation_id=env.correlation_id,
                        created_at=env.created_at,
                        next_role=next_role,
                        governance_state=governance.state,
                        envelope_ballots=ballots,
                    )
            if checkpoint_ok:
                tx.commit()
        await _q_put("q1", q1, env)
        await _q_put("q1", q1, STOP)

    async def architect_task() -> None:
        while True:
            item = await _q_get("q1", q1)
            if item is STOP:
                await _q_put("q2", q2, STOP)
                return
            env1 = item
            engine.validate_envelope(env1, expected_sequence="intake_to_architecture")
            exclude = [governance.root]
            async with WorkspaceTransaction(
                repo_roots=[repo_root],
                token=token,
                stage="architecture_to_risk",
                exclude_roots=exclude,
                proof_ledger=ledger,
            ) as tx:
                payload = await sandbox.run(
                    "software_architect.build_architecture_payload",
                    architect_agent.build_architecture_payload,
                    fn_kwargs={"intake_envelope": env1},
                    timeout_s=stage_timeout_s,
                    mode="thread",
                )
                env2 = engine.create_envelope(
                    sequence="architecture_to_risk",
                    schema_id="architecture_to_risk.v1",
                    payload=payload,
                    source_role="software_architect",
                    correlation_id=env1.correlation_id,
                )
                next_role = stage_to_next_role["architecture_to_risk"]
                hh = _handshake_hash(from_role=env2.source_role, to_role=next_role, schema_id=env2.schema_id, payload=env2.payload)
                try:
                    ballots = await quorum_mgr.validate(
                        stage=env2.sequence,
                        schema=engine.schemas[env2.schema_id],
                        payload=env2.payload,
                        envelope_signature=env2.signature,
                        handshake_hash=hh,
                        source_role=env2.source_role,
                        next_role=next_role,
                        correlation_id=env2.correlation_id,
                        repo_root=repo_root,
                    )
                except QuorumDissentException as exc:
                    if checkpoint is not None:
                        schema = engine.schemas.get(env2.schema_id)
                        if schema is not None:
                            checkpoint.record_quorum_halt(
                                stage=env2.sequence,
                                schema=schema,
                                payload=env2.payload,
                                envelope_signature=env2.signature,
                                source_role=env2.source_role,
                                correlation_id=env2.correlation_id,
                                created_at=env2.created_at,
                                next_role=next_role,
                                envelope_ballots=(exc.ballots if isinstance(exc.ballots, dict) else {}),
                            )
                    raise
                checkpoint_ok = True
                if checkpoint is not None:
                    schema = engine.schemas.get(env2.schema_id)
                    if schema is not None:
                        checkpoint_ok = checkpoint.record_stage(
                            stage=env2.sequence,
                            schema=schema,
                            payload=env2.payload,
                            envelope_signature=env2.signature,
                            source_role=env2.source_role,
                            correlation_id=env2.correlation_id,
                            created_at=env2.created_at,
                            next_role=next_role,
                            governance_state=governance.state,
                            envelope_ballots=ballots,
                        )
                if checkpoint_ok:
                    tx.commit()
                await _q_put("q2", q2, env2)

    async def risk_task() -> None:
        while True:
            item = await _q_get("q2", q2)
            if item is STOP:
                await _q_put("q3", q3, STOP)
                return
            env2 = item
            engine.validate_envelope(env2, expected_sequence="architecture_to_risk")
            exclude = [governance.root]
            async with WorkspaceTransaction(
                repo_roots=[repo_root],
                token=token,
                stage="risk_to_build_execution",
                exclude_roots=exclude,
                proof_ledger=ledger,
            ) as tx:
                payload = await sandbox.run(
                    "risk_compliance.build_risk_payload",
                    risk_agent.build_risk_payload,
                    fn_kwargs={"architecture_envelope": env2},
                    timeout_s=stage_timeout_s,
                    mode="thread",
                )
                env3 = engine.create_envelope(
                    sequence="risk_to_build_execution",
                    schema_id="risk_to_build_execution.v1",
                    payload=payload,
                    source_role="risk_compliance",
                    correlation_id=env2.correlation_id,
                )
                next_role = stage_to_next_role["risk_to_build_execution"]
                hh = _handshake_hash(from_role=env3.source_role, to_role=next_role, schema_id=env3.schema_id, payload=env3.payload)
                try:
                    ballots = await quorum_mgr.validate(
                        stage=env3.sequence,
                        schema=engine.schemas[env3.schema_id],
                        payload=env3.payload,
                        envelope_signature=env3.signature,
                        handshake_hash=hh,
                        source_role=env3.source_role,
                        next_role=next_role,
                        correlation_id=env3.correlation_id,
                        repo_root=repo_root,
                    )
                except QuorumDissentException as exc:
                    if checkpoint is not None:
                        schema = engine.schemas.get(env3.schema_id)
                        if schema is not None:
                            checkpoint.record_quorum_halt(
                                stage=env3.sequence,
                                schema=schema,
                                payload=env3.payload,
                                envelope_signature=env3.signature,
                                source_role=env3.source_role,
                                correlation_id=env3.correlation_id,
                                created_at=env3.created_at,
                                next_role=next_role,
                                envelope_ballots=(exc.ballots if isinstance(exc.ballots, dict) else {}),
                            )
                    raise
                checkpoint_ok = True
                if checkpoint is not None:
                    schema = engine.schemas.get(env3.schema_id)
                    if schema is not None:
                        checkpoint_ok = checkpoint.record_stage(
                            stage=env3.sequence,
                            schema=schema,
                            payload=env3.payload,
                            envelope_signature=env3.signature,
                            source_role=env3.source_role,
                            correlation_id=env3.correlation_id,
                            created_at=env3.created_at,
                            next_role=next_role,
                            governance_state=governance.state,
                            envelope_ballots=ballots,
                        )
                if checkpoint_ok:
                    tx.commit()
                await _q_put("q3", q3, env3)

    async def build_task() -> JSONObject:
        while True:
            item = await _q_get("q3", q3)
            if item is STOP:
                raise CriticalMisalignmentError("Pipeline terminated before build execution.")
            env3 = item
            engine.validate_envelope(env3, expected_sequence="risk_to_build_execution")
            result = await sandbox.run(
                "build_orchestrator.execute_build",
                build_agent.execute_build,
                fn_kwargs={"envelope": env3},
                timeout_s=stage_timeout_s,
                mode="thread",
            )
            if checkpoint is not None:
                checkpoint.clear()
            return result

    async def seed_stop_task() -> None:
        if seed_stop is None:
            return
        if seed_stop is q1:
            await _q_put("q1", q1, STOP)
        elif seed_stop is q2:
            await _q_put("q2", q2, STOP)
        elif seed_stop is q3:
            await _q_put("q3", q3, STOP)
        else:
            await seed_stop.put(STOP)

    async with AgentSandboxExecutor() as sandbox:
        async with asyncio.TaskGroup() as tg:
            if resume is None:
                tg.create_task(intake_task())
                tg.create_task(architect_task())
                tg.create_task(risk_task())
            else:
                if resume.active_stage == "intake_to_architecture":
                    tg.create_task(architect_task())
                    tg.create_task(risk_task())
                elif resume.active_stage == "architecture_to_risk":
                    tg.create_task(risk_task())
                elif resume.active_stage == "risk_to_build_execution":
                    pass
                else:
                    raise CriticalMisalignmentError(f"Unsupported resume stage: {resume.active_stage}")
                tg.create_task(seed_stop_task())
            build = tg.create_task(build_task())

        return build.result()


class TwinAuditor:
    def __init__(self, name: str, validator: SchemaValidator, logs_dir: Path) -> None:
        self._name = name
        self._validator = validator
        self._logs_dir = logs_dir
        self._log = logging.getLogger(name)

    def sign_off(self, schema_file: str, packet: dict, from_agent: str, to_agent: str) -> str:
        self._validator.validate(schema_file, packet)
        provided_hash = packet.get("handshake_hash")
        canonical_packet = packet
        if "handshake_hash" in packet:
            canonical_packet = dict(packet)
            canonical_packet.pop("handshake_hash", None)
        canonical = json.dumps(canonical_packet, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        handshake_hash = fnv1a_32(f"{from_agent}->{to_agent}:{schema_file}:{canonical}")
        if provided_hash is not None:
            if not isinstance(provided_hash, str) or provided_hash != handshake_hash:
                raise PipelineHaltException(
                    f"Handshake hash mismatch for {from_agent}->{to_agent} ({schema_file}): "
                    f"provided={provided_hash!r} expected={handshake_hash!r}"
                )
        self._log.info(
            "Twin-to-Twin Handshake Validated (%s -> %s, %s)",
            from_agent,
            to_agent,
            schema_file,
            extra={"component": self._name, "handshake_hash": handshake_hash},
        )
        return handshake_hash


class HandshakePipeline:
    def __init__(self, schema_dir: Path, logs_dir: Path) -> None:
        self._schema_dir = schema_dir
        self._logs_dir = logs_dir
        self._validator = SchemaValidator(schema_dir)

    async def run(self, isa, sas, crs, boa, source_text: str, repository_name: str | None = None) -> dict:
        state: dict = {"pipeline_state": "RUNNING", "telemetry": []}
        stage_timeout_s = 5.0
        tasks: list[asyncio.Task[Any]] = []
        artifact_task: asyncio.Task[Any] | None = None

        q_isa_out: asyncio.Queue = asyncio.Queue()
        q_sas_in: asyncio.Queue = asyncio.Queue()
        q_sas_out: asyncio.Queue = asyncio.Queue()
        q_crs_in: asyncio.Queue = asyncio.Queue()
        q_crs_out: asyncio.Queue = asyncio.Queue()
        q_boa_in: asyncio.Queue = asyncio.Queue()

        ita = TwinAuditor("ITA", self._validator, self._logs_dir)
        ata = TwinAuditor("ATA", self._validator, self._logs_dir)
        rta = TwinAuditor("RTA", self._validator, self._logs_dir)

        async def _isa_task() -> None:
            packet = await sandbox.run(
                "ISA.ingest",
                isa.ingest,
                fn_kwargs={"source_text": source_text, "repository_name": repository_name},
                timeout_s=stage_timeout_s,
                mode="auto",
            )
            state["isa_packet"] = packet
            await q_isa_out.put(packet)
            await q_isa_out.put(None)

        async def _auditor_task(
            auditor: TwinAuditor,
            schema_file: str,
            from_agent: str,
            to_agent: str,
            q_in: asyncio.Queue,
            q_out: asyncio.Queue,
        ) -> None:
            while True:
                pkt = await q_in.get()
                if pkt is None:
                    await q_out.put(None)
                    return
                handshake_hash = auditor.sign_off(
                    schema_file=schema_file,
                    packet=pkt,
                    from_agent=from_agent,
                    to_agent=to_agent,
                )
                state["telemetry"].append(
                    {
                        "from": from_agent,
                        "to": to_agent,
                        "schema": schema_file,
                        "handshake_hash": handshake_hash,
                    }
                )
                await q_out.put(pkt)

        async def _sas_task() -> None:
            while True:
                pkt = await q_sas_in.get()
                if pkt is None:
                    await q_sas_out.put(None)
                    return
                blueprint = await sandbox.run(
                    "SAS.process",
                    sas.process,
                    pkt,
                    timeout_s=stage_timeout_s,
                    mode="auto",
                )
                state["sas_packet"] = blueprint
                await q_sas_out.put(blueprint)

        async def _crs_task() -> None:
            while True:
                pkt = await q_crs_in.get()
                if pkt is None:
                    await q_crs_out.put(None)
                    return
                clearance = await sandbox.run(
                    "CRS.assess",
                    crs.assess,
                    pkt,
                    timeout_s=stage_timeout_s,
                    mode="auto",
                )
                state["crs_packet"] = clearance
                await q_crs_out.put(clearance)

        async def _boa_task() -> dict:
            while True:
                pkt = await q_boa_in.get()
                if pkt is None:
                    raise PipelineHaltException("BOA received no clearance packet")
                artifact = await sandbox.run(
                    "BOA.build",
                    boa.build,
                    pkt,
                    fn_kwargs={"telemetry": state.get("telemetry", [])},
                    timeout_s=stage_timeout_s,
                    mode="auto",
                )
                state["pipeline_state"] = "COMPLETED"
                state["artifact"] = artifact
                return artifact

        try:
            async with AgentSandboxExecutor() as sandbox:
                tasks = [
                    asyncio.create_task(_isa_task()),
                    asyncio.create_task(_auditor_task(ita, "intake_handshake.json", "ISA", "SAS", q_isa_out, q_sas_in)),
                    asyncio.create_task(_sas_task()),
                    asyncio.create_task(
                        _auditor_task(ata, "architecture_blueprint.json", "SAS", "CRS", q_sas_out, q_crs_in)
                    ),
                    asyncio.create_task(_crs_task()),
                    asyncio.create_task(_auditor_task(rta, "risk_clearance.json", "CRS", "BOA", q_crs_out, q_boa_in)),
                ]
                artifact_task = asyncio.create_task(_boa_task())
                await asyncio.gather(*tasks)
                return await artifact_task
        except Exception as exc:
            for task in tasks:
                task.cancel()
            try:
                if artifact_task is not None:
                    artifact_task.cancel()
            except Exception:
                pass
            await asyncio.gather(*tasks, *( [artifact_task] if artifact_task is not None else [] ), return_exceptions=True)
            state["pipeline_state"] = "DEAD_HALT"
            dump_critical_misalignment(self._logs_dir, state, exc)
            raise
