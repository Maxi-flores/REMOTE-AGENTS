from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List


PRIORITIES = {"P0", "P1", "P2", "P3", "P4"}


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


@dataclass
class GovernanceRecoveryAction:
    action_id: str
    source_component_id: str
    title: str
    description: str
    priority: str
    expected_score_impact: int
    target_component: str
    recommended_commands: List[str]
    validation_focus: List[str]
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "source_component_id": self.source_component_id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "expected_score_impact": int(self.expected_score_impact),
            "target_component": self.target_component,
            "recommended_commands": list(self.recommended_commands),
            "validation_focus": list(self.validation_focus),
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


@dataclass
class GovernanceRecoveryWave:
    wave_id: str
    title: str
    objective: str
    priority: str
    actions: List[str]
    expected_score_impact: int
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "wave_id": self.wave_id,
            "title": self.title,
            "objective": self.objective,
            "priority": self.priority,
            "actions": list(self.actions),
            "expected_score_impact": int(self.expected_score_impact),
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


@dataclass
class GovernanceRecoveryPlanReport:
    report_id: str
    generated_utc: str
    source_governance_report_id: str
    current_governance_score: int
    target_governance_score: int
    actions: List[Dict[str, Any]]
    waves: List[Dict[str, Any]]
    recommended_sequence: List[str]
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "generated_utc": self.generated_utc,
            "source_governance_report_id": self.source_governance_report_id,
            "current_governance_score": int(self.current_governance_score),
            "target_governance_score": int(self.target_governance_score),
            "actions": list(self.actions),
            "waves": list(self.waves),
            "recommended_sequence": list(self.recommended_sequence),
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


def validate_governance_recovery_action_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "action_id")
    _require_str(payload, "source_component_id")
    _require_str(payload, "title")
    _require_str(payload, "description")
    p = _require_str(payload, "priority")
    if p not in PRIORITIES:
        raise ValueError(f"invalid priority: {p}")
    _require_int(payload, "expected_score_impact")
    _require_str(payload, "target_component")
    _require_list(payload, "recommended_commands")
    _require_list(payload, "validation_focus")
    _require_bool(payload, "advisory_only")
    _require_dict(payload, "metadata")


def validate_governance_recovery_wave_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "wave_id")
    _require_str(payload, "title")
    _require_str(payload, "objective")
    p = _require_str(payload, "priority")
    if p not in PRIORITIES:
        raise ValueError(f"invalid priority: {p}")
    _require_list(payload, "actions")
    _require_int(payload, "expected_score_impact")
    _require_bool(payload, "advisory_only")
    _require_dict(payload, "metadata")


def validate_governance_recovery_plan_report_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "report_id")
    _require_str(payload, "generated_utc")
    _require_str(payload, "source_governance_report_id")
    _require_int(payload, "current_governance_score")
    _require_int(payload, "target_governance_score")
    _require_list(payload, "actions")
    for action in payload["actions"]:
        if isinstance(action, dict):
            validate_governance_recovery_action_dict(action)
    _require_list(payload, "waves")
    for wave in payload["waves"]:
        if isinstance(wave, dict):
            validate_governance_recovery_wave_dict(wave)
    _require_list(payload, "recommended_sequence")
    _require_bool(payload, "advisory_only")
    _require_dict(payload, "metadata")


def _require_str(payload: Dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} required")
    return value


def _require_int(payload: Dict[str, Any], key: str) -> None:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{key} must be integer")


def _require_list(payload: Dict[str, Any], key: str) -> None:
    if not isinstance(payload.get(key), list):
        raise ValueError(f"{key} must be list")


def _require_bool(payload: Dict[str, Any], key: str) -> None:
    if not isinstance(payload.get(key), bool):
        raise ValueError(f"{key} must be bool")


def _require_dict(payload: Dict[str, Any], key: str) -> None:
    if not isinstance(payload.get(key), dict):
        raise ValueError(f"{key} must be dict")

