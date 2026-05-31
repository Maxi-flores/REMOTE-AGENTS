from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List


EXECUTION_RISKS = {"low", "medium", "high", "critical"}


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


@dataclass
class GovernanceRecoveryDossier:
    dossier_id: str
    source_action_id: str
    source_wave_id: str
    title: str
    objective: str
    target_component: str
    target_artifacts: List[str]
    recommended_commands: List[str]
    validation_commands: List[str]
    review_checklist: List[str]
    rollback_guidance: List[str]
    codex_prompt: str
    execution_risk: str
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dossier_id": self.dossier_id,
            "source_action_id": self.source_action_id,
            "source_wave_id": self.source_wave_id,
            "title": self.title,
            "objective": self.objective,
            "target_component": self.target_component,
            "target_artifacts": list(self.target_artifacts),
            "recommended_commands": list(self.recommended_commands),
            "validation_commands": list(self.validation_commands),
            "review_checklist": list(self.review_checklist),
            "rollback_guidance": list(self.rollback_guidance),
            "codex_prompt": self.codex_prompt,
            "execution_risk": self.execution_risk,
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


@dataclass
class GovernanceRecoveryDossierReport:
    report_id: str
    generated_utc: str
    source_recovery_report_id: str
    dossiers: List[Dict[str, Any]]
    wave_summary: List[Dict[str, Any]]
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "generated_utc": self.generated_utc,
            "source_recovery_report_id": self.source_recovery_report_id,
            "dossiers": list(self.dossiers),
            "wave_summary": list(self.wave_summary),
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


def validate_governance_recovery_dossier_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "dossier_id")
    _require_str(payload, "source_action_id")
    _require_str(payload, "source_wave_id")
    _require_str(payload, "title")
    _require_str(payload, "objective")
    _require_str(payload, "target_component")
    _require_list(payload, "target_artifacts")
    _require_list(payload, "recommended_commands")
    _require_list(payload, "validation_commands")
    _require_list(payload, "review_checklist")
    _require_list(payload, "rollback_guidance")
    _require_str(payload, "codex_prompt")
    risk = _require_str(payload, "execution_risk")
    if risk not in EXECUTION_RISKS:
        raise ValueError(f"invalid execution_risk: {risk}")
    advisory_only = payload.get("advisory_only")
    if advisory_only is not True:
        raise ValueError("advisory_only must be true")
    _require_dict(payload, "metadata")


def validate_governance_recovery_dossier_report_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "report_id")
    _require_str(payload, "generated_utc")
    _require_str(payload, "source_recovery_report_id")
    _require_list(payload, "dossiers")
    for dossier in payload["dossiers"]:
        if isinstance(dossier, dict):
            validate_governance_recovery_dossier_dict(dossier)
    _require_list(payload, "wave_summary")
    _require_bool(payload, "advisory_only")
    _require_dict(payload, "metadata")


def _require_str(payload: Dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} required")
    return value


def _require_list(payload: Dict[str, Any], key: str) -> None:
    if not isinstance(payload.get(key), list):
        raise ValueError(f"{key} must be list")


def _require_bool(payload: Dict[str, Any], key: str) -> None:
    if not isinstance(payload.get(key), bool):
        raise ValueError(f"{key} must be bool")


def _require_dict(payload: Dict[str, Any], key: str) -> None:
    if not isinstance(payload.get(key), dict):
        raise ValueError(f"{key} must be dict")

