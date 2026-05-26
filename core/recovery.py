"""Transactional checkpointing and crash recovery for the orchestrator pipeline.

This module is intentionally stdlib-only (Python 3.10+) and provides:
- Atomic checkpoint snapshots written to logs/checkpoint_state.json
- Idempotent resume hints for the stage queues in core/handshake.py
- Optional intervention resolution for previously halted governance states
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Mapping, TypedDict, cast

from core.hashutil import fnv1a_32
from core.schema import Schema, SchemaValidationError, canonical_json, signature_for, validate_against_schema
from core.types import JSONObject, JSONValue

CheckpointStage = Literal["intake_to_architecture", "architecture_to_risk", "risk_to_build_execution"]
GovernanceState = Literal["Running", "Pending Intervention", "Completed"]


class CheckpointFormatError(ValueError):
    pass


class CheckpointConflictError(RuntimeError):
    pass


class _CheckpointJSON(TypedDict, total=False):
    version: int
    execution_token: str
    governance_state: str
    active_stage: str
    schema_id: str
    payload: object
    envelope_signature: str
    handshake_hash: str
    source_role: str
    correlation_id: str
    created_at: float
    updated_at: float


@dataclass(frozen=True, slots=True)
class CheckpointSnapshot:
    version: int
    execution_token: str
    governance_state: GovernanceState
    active_stage: CheckpointStage
    schema_id: str
    payload: JSONObject
    envelope_signature: str
    handshake_hash: str
    source_role: str
    correlation_id: str
    created_at: float
    updated_at: float

    def to_json(self) -> _CheckpointJSON:
        return {
            "version": self.version,
            "execution_token": self.execution_token,
            "governance_state": self.governance_state,
            "active_stage": self.active_stage,
            "schema_id": self.schema_id,
            "payload": self.payload,
            "envelope_signature": self.envelope_signature,
            "handshake_hash": self.handshake_hash,
            "source_role": self.source_role,
            "correlation_id": self.correlation_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


def execution_token(*, business_case: str) -> str:
    material = business_case.strip().encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def _handshake_hash(
    *,
    from_role: str,
    to_role: str,
    schema_id: str,
    payload: JSONValue,
) -> str:
    canonical = canonical_json(payload)
    return fnv1a_32(f"{from_role}->{to_role}:{schema_id}:{canonical}")


def _atomic_write_json(path: Path, obj: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    tmp_fd: int | None = None
    tmp_path: str | None = None
    try:
        fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
        tmp_fd = fd
        tmp_path = tmp
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if tmp_fd is not None:
            # fd already closed by fdopen()
            tmp_fd = None
        if tmp_path is not None:
            try:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            except OSError:
                pass


def _read_json_file(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _as_str(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise CheckpointFormatError(f"Invalid {field}.")
    return value


def _as_float(value: object, *, field: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise CheckpointFormatError(f"Invalid {field}.")
    return float(value)


def _as_payload(value: object) -> JSONObject:
    if not isinstance(value, dict):
        raise CheckpointFormatError("Invalid payload.")
    return cast(JSONObject, value)


class CheckpointManager:
    """Write/restore transactional checkpoints for the orchestrator pipeline."""

    _VERSION = 1

    def __init__(self, *, logs_dir: Path, business_case: str) -> None:
        self._logs_dir = logs_dir
        self._token = execution_token(business_case=business_case)

    @property
    def checkpoint_path(self) -> Path:
        return self._logs_dir / "checkpoint_state.json"

    @property
    def token(self) -> str:
        return self._token

    def load(self) -> CheckpointSnapshot | None:
        path = self.checkpoint_path
        if not path.exists():
            return None
        raw = _read_json_file(path)
        if not isinstance(raw, dict):
            raise CheckpointFormatError("Checkpoint file must be a JSON object.")

        obj: _CheckpointJSON = cast(_CheckpointJSON, raw)
        version = obj.get("version")
        if version != self._VERSION:
            raise CheckpointFormatError("Unsupported checkpoint version.")

        token = _as_str(obj.get("execution_token"), field="execution_token")
        if token != self._token:
            return None

        stage = _as_str(obj.get("active_stage"), field="active_stage")
        if stage not in ("intake_to_architecture", "architecture_to_risk", "risk_to_build_execution"):
            raise CheckpointFormatError("Invalid active_stage.")

        governance_state = _as_str(obj.get("governance_state"), field="governance_state")
        if governance_state not in ("Running", "Pending Intervention", "Completed"):
            raise CheckpointFormatError("Invalid governance_state.")

        schema_id = _as_str(obj.get("schema_id"), field="schema_id")
        payload = _as_payload(obj.get("payload"))
        envelope_signature = _as_str(obj.get("envelope_signature"), field="envelope_signature")
        handshake_hash = _as_str(obj.get("handshake_hash"), field="handshake_hash")
        source_role = _as_str(obj.get("source_role"), field="source_role")
        correlation_id = _as_str(obj.get("correlation_id"), field="correlation_id")
        created_at = _as_float(obj.get("created_at"), field="created_at")
        updated_at = _as_float(obj.get("updated_at"), field="updated_at")

        return CheckpointSnapshot(
            version=self._VERSION,
            execution_token=token,
            governance_state=cast(GovernanceState, governance_state),
            active_stage=cast(CheckpointStage, stage),
            schema_id=schema_id,
            payload=payload,
            envelope_signature=envelope_signature,
            handshake_hash=handshake_hash,
            source_role=source_role,
            correlation_id=correlation_id,
            created_at=created_at,
            updated_at=updated_at,
        )

    def record_stage(
        self,
        *,
        stage: CheckpointStage,
        schema: Schema,
        payload: JSONObject,
        envelope_signature: str,
        source_role: str,
        correlation_id: str,
        created_at: float,
        next_role: str,
        governance_state: GovernanceState = "Running",
    ) -> None:
        """Atomically persist a checkpoint after a successful stage handoff."""
        try:
            validate_against_schema(payload, schema.definition)
            expected_sig = signature_for(schema, payload)
            if envelope_signature != expected_sig:
                raise CheckpointConflictError("Envelope signature mismatch while checkpointing.")
            hh = _handshake_hash(
                from_role=source_role,
                to_role=next_role,
                schema_id=schema.schema_id,
                payload=payload,
            )
            now = time.time()
            snap = CheckpointSnapshot(
                version=self._VERSION,
                execution_token=self._token,
                governance_state=governance_state,
                active_stage=stage,
                schema_id=schema.schema_id,
                payload=payload,
                envelope_signature=envelope_signature,
                handshake_hash=hh,
                source_role=source_role,
                correlation_id=correlation_id,
                created_at=created_at,
                updated_at=now,
            )
            _atomic_write_json(self.checkpoint_path, snap.to_json())
        except Exception:
            # Recovery must never cause a new halt; containment is required.
            return

    def clear(self) -> None:
        try:
            self.checkpoint_path.unlink(missing_ok=True)
        except Exception:
            return

    def resolve_intervention(self, *, schemas: Mapping[str, Schema]) -> CheckpointSnapshot | None:
        """Re-validate a human-edited payload and flip governance_state back to Running."""
        snap = self.load()
        if snap is None:
            return None

        schema = schemas.get(snap.schema_id)
        if schema is None:
            raise CheckpointFormatError(f"Unknown schema_id in checkpoint: {snap.schema_id}")

        # Validate the (possibly edited) payload and re-sign it deterministically.
        validate_against_schema(snap.payload, schema.definition)
        new_sig = signature_for(schema, snap.payload)

        # Recompute handshake hash with a conservative role mapping.
        stage_to_next = {
            "intake_to_architecture": "software_architect",
            "architecture_to_risk": "risk_compliance",
            "risk_to_build_execution": "build_orchestrator",
        }
        next_role = stage_to_next.get(snap.active_stage, "unknown")
        hh = _handshake_hash(
            from_role=snap.source_role,
            to_role=next_role,
            schema_id=schema.schema_id,
            payload=snap.payload,
        )

        repaired = CheckpointSnapshot(
            version=self._VERSION,
            execution_token=snap.execution_token,
            governance_state="Running",
            active_stage=snap.active_stage,
            schema_id=schema.schema_id,
            payload=snap.payload,
            envelope_signature=new_sig,
            handshake_hash=hh,
            source_role=snap.source_role,
            correlation_id=snap.correlation_id,
            created_at=snap.created_at,
            updated_at=time.time(),
        )
        _atomic_write_json(self.checkpoint_path, repaired.to_json())
        return repaired

    def requires_manual_intervention(self) -> bool:
        """Return True when governance.jsonl indicates a CRITICAL_MISALIGNMENT halt."""
        path = self._logs_dir / "governance.jsonl"
        if not path.exists():
            return False
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return False

        saw_pending = False
        saw_misalignment = False
        for ln in lines[-500:]:
            try:
                obj = json.loads(ln)
            except Exception:
                continue
            if not isinstance(obj, dict):
                continue
            if obj.get("event") == "CRITICAL_MISALIGNMENT":
                saw_misalignment = True
            if obj.get("event") == "STATE" and obj.get("state") == "Pending Intervention":
                saw_pending = True
        return saw_pending and saw_misalignment

