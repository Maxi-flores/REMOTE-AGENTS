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

from .exceptions import CriticalMisalignmentError, PipelineHaltException
from .fault import dump_critical_misalignment
from .governance import GovernanceLogger
from .hashutil import fnv1a_32
from .schema import Schema, SchemaValidationError, signature_for, validate_against_schema
from .types import JSONObject
from .validator import SchemaValidator

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
) -> JSONObject:
    engine = HandshakeEngine(governance=governance, schemas=handshake_schemas())

    q1: asyncio.Queue[PacketEnvelope[JSONObject] | _Stop] = asyncio.Queue(maxsize=1)
    q2: asyncio.Queue[PacketEnvelope[JSONObject] | _Stop] = asyncio.Queue(maxsize=1)
    q3: asyncio.Queue[PacketEnvelope[JSONObject] | _Stop] = asyncio.Queue(maxsize=1)

    async def intake_task() -> None:
        payload = await intake_agent.build_intake_payload(
            business_case=business_case, workspace_snapshot=workspace_snapshot
        )
        env = engine.create_envelope(
            sequence="intake_to_architecture",
            schema_id="intake_to_architecture.v1",
            payload=payload,
            source_role="intake_specialist",
        )
        await q1.put(env)
        await q1.put(STOP)

    async def architect_task() -> None:
        while True:
            item = await q1.get()
            if item is STOP:
                await q2.put(STOP)
                return
            env1 = item
            engine.validate_envelope(env1, expected_sequence="intake_to_architecture")
            payload = await architect_agent.build_architecture_payload(intake_envelope=env1)
            env2 = engine.create_envelope(
                sequence="architecture_to_risk",
                schema_id="architecture_to_risk.v1",
                payload=payload,
                source_role="software_architect",
                correlation_id=env1.correlation_id,
            )
            await q2.put(env2)

    async def risk_task() -> None:
        while True:
            item = await q2.get()
            if item is STOP:
                await q3.put(STOP)
                return
            env2 = item
            engine.validate_envelope(env2, expected_sequence="architecture_to_risk")
            payload = await risk_agent.build_risk_payload(architecture_envelope=env2)
            env3 = engine.create_envelope(
                sequence="risk_to_build_execution",
                schema_id="risk_to_build_execution.v1",
                payload=payload,
                source_role="risk_compliance",
                correlation_id=env2.correlation_id,
            )
            await q3.put(env3)

    async def build_task() -> JSONObject:
        while True:
            item = await q3.get()
            if item is STOP:
                raise CriticalMisalignmentError("Pipeline terminated before build execution.")
            env3 = item
            engine.validate_envelope(env3, expected_sequence="risk_to_build_execution")
            return await build_agent.execute_build(envelope=env3)

    async with asyncio.TaskGroup() as tg:
        tg.create_task(intake_task())
        tg.create_task(architect_task())
        tg.create_task(risk_task())
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
            packet = isa.ingest(source_text=source_text, repository_name=repository_name)
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
                blueprint = sas.process(pkt)
                state["sas_packet"] = blueprint
                await q_sas_out.put(blueprint)

        async def _crs_task() -> None:
            while True:
                pkt = await q_crs_in.get()
                if pkt is None:
                    await q_crs_out.put(None)
                    return
                clearance = crs.assess(pkt)
                state["crs_packet"] = clearance
                await q_crs_out.put(clearance)

        async def _boa_task() -> dict:
            while True:
                pkt = await q_boa_in.get()
                if pkt is None:
                    raise PipelineHaltException("BOA received no clearance packet")
                artifact = boa.build(pkt, telemetry=state.get("telemetry", []))
                state["pipeline_state"] = "COMPLETED"
                state["artifact"] = artifact
                return artifact

        try:
            tasks = [
                asyncio.create_task(_isa_task()),
                asyncio.create_task(_auditor_task(ita, "intake_handshake.json", "ISA", "SAS", q_isa_out, q_sas_in)),
                asyncio.create_task(_sas_task()),
                asyncio.create_task(_auditor_task(ata, "architecture_blueprint.json", "SAS", "CRS", q_sas_out, q_crs_in)),
                asyncio.create_task(_crs_task()),
                asyncio.create_task(_auditor_task(rta, "risk_clearance.json", "CRS", "BOA", q_crs_out, q_boa_in)),
            ]
            artifact_task = asyncio.create_task(_boa_task())
            await asyncio.gather(*tasks)
            return await artifact_task
        except Exception as exc:
            state["pipeline_state"] = "DEAD_HALT"
            dump_critical_misalignment(self._logs_dir, state, exc)
            raise
