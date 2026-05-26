"""Twin-to-twin async handshake pipeline with strict validation.

The pipeline emits three deterministic envelope types:
1) Intake-to-Architecture Packet
2) Architecture-to-Risk Packet
3) Risk-to-Build Execution Packet
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass
from typing import Any, Generic, Literal, TypeVar

from core.exceptions import CriticalMisalignmentError
from core.governance import GovernanceLogger
from core.schema import Schema, SchemaValidationError, signature_for, validate_against_schema
from core.types import JSONValue, JSONObject

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
        except SchemaValidationError as e:
            self.governance.emit_event(
                {
                    "event": "HANDSHAKE_PAYLOAD_SCHEMA_ERROR",
                    "sequence": sequence,
                    "schema_id": schema.schema_id,
                    "error": str(e),
                    "source_role": source_role,
                }
            )
            raise CriticalMisalignmentError(str(e)) from e


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
