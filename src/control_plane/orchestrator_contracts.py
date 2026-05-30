from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List


TRIGGER_SOURCES = {"manual", "mission_cli", "snapshot_refresh", "unknown"}
STAGE_NAMES = {
    "mission",
    "scheduler",
    "tool_router",
    "governance",
    "memory_graph",
    "release_readiness",
    "release_gates",
    "release_center",
    "lifecycle",
    "snapshot",
    "sentient_ui",
}
STAGE_STATUSES = {"not_run", "ok", "warning", "blocked", "error", "unknown"}
PIPELINE_STATUSES = {"ok", "warning", "blocked", "error", "unknown"}


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


@dataclass
class ControlPlaneOrchestrationRequest:
    orchestration_id: str
    trigger_source: str
    task_ids: List[str]
    target_repositories: List[str]
    requested_utc: str
    advisory_only: bool = True
    mission_id: str | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "orchestration_id": self.orchestration_id,
            "trigger_source": self.trigger_source,
            "mission_id": self.mission_id,
            "task_ids": list(self.task_ids),
            "target_repositories": list(self.target_repositories),
            "requested_utc": self.requested_utc,
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


@dataclass
class ControlPlaneOrchestrationStageResult:
    stage_name: str
    status: str
    input_refs: List[str]
    output_refs: List[str]
    warnings: List[str]
    blockers: List[str]
    summary: Dict[str, Any]
    completed_utc: str
    advisory_only: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage_name": self.stage_name,
            "status": self.status,
            "input_refs": list(self.input_refs),
            "output_refs": list(self.output_refs),
            "warnings": list(self.warnings),
            "blockers": list(self.blockers),
            "summary": dict(self.summary),
            "completed_utc": self.completed_utc,
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


@dataclass
class ControlPlaneOrchestrationReport:
    report_id: str
    orchestration_id: str
    generated_utc: str
    pipeline_status: str
    stage_results: List[Dict[str, Any]]
    cross_stage_findings: List[str]
    recommended_next_actions: List[str]
    advisory_only: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "orchestration_id": self.orchestration_id,
            "generated_utc": self.generated_utc,
            "pipeline_status": self.pipeline_status,
            "stage_results": list(self.stage_results),
            "cross_stage_findings": list(self.cross_stage_findings),
            "recommended_next_actions": list(self.recommended_next_actions),
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


def validate_orchestration_request_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "orchestration_id")
    trigger = _require_str(payload, "trigger_source")
    if trigger not in TRIGGER_SOURCES:
        raise ValueError(f"invalid trigger_source: {trigger}")
    _require_str(payload, "requested_utc")
    _require_list(payload, "task_ids")
    _require_list(payload, "target_repositories")
    _require_advisory_only(payload)
    _require_dict(payload, "metadata")


def validate_orchestration_stage_result_dict(payload: Dict[str, Any]) -> None:
    stage = _require_str(payload, "stage_name")
    if stage not in STAGE_NAMES:
        raise ValueError(f"invalid stage_name: {stage}")
    status = _require_str(payload, "status")
    if status not in STAGE_STATUSES:
        raise ValueError(f"invalid stage status: {status}")
    _require_list(payload, "input_refs")
    _require_list(payload, "output_refs")
    _require_list(payload, "warnings")
    _require_list(payload, "blockers")
    _require_dict(payload, "summary")
    _require_str(payload, "completed_utc")
    _require_advisory_only(payload)
    _require_dict(payload, "metadata")


def validate_orchestration_report_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "report_id")
    _require_str(payload, "orchestration_id")
    _require_str(payload, "generated_utc")
    status = _require_str(payload, "pipeline_status")
    if status not in PIPELINE_STATUSES:
        raise ValueError(f"invalid pipeline_status: {status}")
    _require_list(payload, "stage_results")
    for stage in payload.get("stage_results", []):
        if isinstance(stage, dict):
            validate_orchestration_stage_result_dict(stage)
    _require_list(payload, "cross_stage_findings")
    _require_list(payload, "recommended_next_actions")
    _require_advisory_only(payload)
    _require_dict(payload, "metadata")


def _require_str(payload: Dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} required")
    return value


def _require_list(payload: Dict[str, Any], key: str) -> None:
    if not isinstance(payload.get(key), list):
        raise ValueError(f"{key} must be list")


def _require_dict(payload: Dict[str, Any], key: str) -> None:
    if not isinstance(payload.get(key, {}), dict):
        raise ValueError(f"{key} must be dict")


def _require_advisory_only(payload: Dict[str, Any]) -> None:
    if payload.get("advisory_only") is not True:
        raise ValueError("advisory_only must be true")

