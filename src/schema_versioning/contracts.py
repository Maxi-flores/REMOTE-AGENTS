from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal


ArtifactType = Literal[
    "control_plane_snapshot",
    "control_plane_snapshot_jsonl",
    "sentient_ui_view_model",
    "sentient_ui_view_model_jsonl",
]
MigrationStatus = Literal["not_required", "planned", "blocked", "unsupported", "dry_run_only"]

ARTIFACT_TYPES = {
    "control_plane_snapshot",
    "control_plane_snapshot_jsonl",
    "sentient_ui_view_model",
    "sentient_ui_view_model_jsonl",
}
MIGRATION_STATUSES = {"not_required", "planned", "blocked", "unsupported", "dry_run_only"}


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


@dataclass
class SchemaManifest:
    schema_id: str
    artifact_type: ArtifactType
    current_version: int
    supported_versions: List[int]
    deprecated_versions: List[int] = field(default_factory=list)
    required_fields: List[str] = field(default_factory=list)
    optional_fields: List[str] = field(default_factory=list)
    compatibility_notes: List[str] = field(default_factory=list)
    created_utc: str = field(default_factory=utc_now)
    updated_utc: str = field(default_factory=utc_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "artifact_type": self.artifact_type,
            "current_version": int(self.current_version),
            "supported_versions": list(self.supported_versions),
            "deprecated_versions": list(self.deprecated_versions),
            "required_fields": list(self.required_fields),
            "optional_fields": list(self.optional_fields),
            "compatibility_notes": list(self.compatibility_notes),
            "created_utc": self.created_utc,
            "updated_utc": self.updated_utc,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "SchemaManifest":
        validate_schema_manifest_dict(payload)
        return cls(
            schema_id=payload["schema_id"],
            artifact_type=payload["artifact_type"],
            current_version=int(payload["current_version"]),
            supported_versions=[int(v) for v in payload.get("supported_versions", [])],
            deprecated_versions=[int(v) for v in payload.get("deprecated_versions", [])],
            required_fields=[str(v) for v in payload.get("required_fields", [])],
            optional_fields=[str(v) for v in payload.get("optional_fields", [])],
            compatibility_notes=[str(v) for v in payload.get("compatibility_notes", [])],
            created_utc=str(payload.get("created_utc") or utc_now()),
            updated_utc=str(payload.get("updated_utc") or utc_now()),
            metadata=dict(payload.get("metadata") or {}),
        )


@dataclass
class CompatibilityCheckResult:
    result_id: str
    artifact_type: ArtifactType
    artifact_path: str
    detected_version: int | None
    expected_version: int | None
    is_compatible: bool
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    checked_utc: str = field(default_factory=utc_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "artifact_type": self.artifact_type,
            "artifact_path": self.artifact_path,
            "detected_version": self.detected_version,
            "expected_version": self.expected_version,
            "is_compatible": bool(self.is_compatible),
            "issues": list(self.issues),
            "warnings": list(self.warnings),
            "checked_utc": self.checked_utc,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "CompatibilityCheckResult":
        validate_compatibility_check_result_dict(payload)
        return cls(
            result_id=payload["result_id"],
            artifact_type=payload["artifact_type"],
            artifact_path=payload["artifact_path"],
            detected_version=payload.get("detected_version"),
            expected_version=payload.get("expected_version"),
            is_compatible=bool(payload.get("is_compatible")),
            issues=[str(v) for v in payload.get("issues", [])],
            warnings=[str(v) for v in payload.get("warnings", [])],
            checked_utc=payload["checked_utc"],
            metadata=dict(payload.get("metadata") or {}),
        )


@dataclass
class MigrationPlan:
    plan_id: str
    artifact_type: ArtifactType
    artifact_path: str
    from_version: int | None
    to_version: int
    migration_status: MigrationStatus
    steps: List[str] = field(default_factory=list)
    destructive: bool = False
    created_utc: str = field(default_factory=utc_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "artifact_type": self.artifact_type,
            "artifact_path": self.artifact_path,
            "from_version": self.from_version,
            "to_version": int(self.to_version),
            "migration_status": self.migration_status,
            "steps": list(self.steps),
            "destructive": bool(self.destructive),
            "created_utc": self.created_utc,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "MigrationPlan":
        validate_migration_plan_dict(payload)
        return cls(
            plan_id=payload["plan_id"],
            artifact_type=payload["artifact_type"],
            artifact_path=payload["artifact_path"],
            from_version=payload.get("from_version"),
            to_version=int(payload.get("to_version", 1)),
            migration_status=payload["migration_status"],
            steps=[str(v) for v in payload.get("steps", [])],
            destructive=bool(payload.get("destructive")),
            created_utc=str(payload.get("created_utc") or utc_now()),
            metadata=dict(payload.get("metadata") or {}),
        )


def validate_schema_manifest_dict(payload: Dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ValueError("SchemaManifest must be an object")
    _require_str(payload, "schema_id")
    artifact_type = _require_str(payload, "artifact_type")
    if artifact_type not in ARTIFACT_TYPES:
        raise ValueError(f"invalid artifact_type: {artifact_type}")
    for key in ("supported_versions", "deprecated_versions", "required_fields", "optional_fields", "compatibility_notes"):
        if not isinstance(payload.get(key, []), list):
            raise ValueError(f"{key} must be a list")
    if isinstance(payload.get("current_version"), bool) or not isinstance(payload.get("current_version"), int):
        raise ValueError("current_version required")
    if not isinstance(payload.get("metadata", {}), dict):
        raise ValueError("metadata must be an object")


def validate_compatibility_check_result_dict(payload: Dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ValueError("CompatibilityCheckResult must be an object")
    _require_str(payload, "result_id")
    artifact_type = _require_str(payload, "artifact_type")
    if artifact_type not in ARTIFACT_TYPES:
        raise ValueError(f"invalid artifact_type: {artifact_type}")
    _require_str(payload, "artifact_path")
    for key in ("issues", "warnings"):
        if not isinstance(payload.get(key, []), list):
            raise ValueError(f"{key} must be a list")
    _require_str(payload, "checked_utc")
    if not isinstance(payload.get("metadata", {}), dict):
        raise ValueError("metadata must be an object")


def validate_migration_plan_dict(payload: Dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ValueError("MigrationPlan must be an object")
    _require_str(payload, "plan_id")
    artifact_type = _require_str(payload, "artifact_type")
    if artifact_type not in ARTIFACT_TYPES:
        raise ValueError(f"invalid artifact_type: {artifact_type}")
    _require_str(payload, "artifact_path")
    status = _require_str(payload, "migration_status")
    if status not in MIGRATION_STATUSES:
        raise ValueError(f"invalid migration_status: {status}")
    if not isinstance(payload.get("steps", []), list):
        raise ValueError("steps must be a list")
    if not isinstance(payload.get("destructive"), bool):
        raise ValueError("destructive must be bool")
    if not isinstance(payload.get("metadata", {}), dict):
        raise ValueError("metadata must be an object")


def _require_str(payload: Dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} is required")
    return value

