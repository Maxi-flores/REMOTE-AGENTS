from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal


TargetEnvironment = Literal["dev", "staging", "production"]
PromotionDecision = Literal["promote", "promote_with_warnings", "hold", "blocked", "unknown"]
ConfidenceLevel = Literal["low", "medium", "high"]

TARGET_ENVIRONMENTS = {"dev", "staging", "production"}
PROMOTION_DECISIONS = {"promote", "promote_with_warnings", "hold", "blocked", "unknown"}
CONFIDENCE_LEVELS = {"low", "medium", "high"}


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


@dataclass
class PromotionProfile:
    profile_id: str
    display_name: str
    target_environment: TargetEnvironment
    required_scenario_pack: str
    minimum_aggregate_status: str
    allowed_aggregate_decisions: List[str]
    require_no_blockers: bool
    require_rollback_plan: bool
    require_ci_handoff: bool
    max_warning_count: int
    max_error_count: int
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "display_name": self.display_name,
            "target_environment": self.target_environment,
            "required_scenario_pack": self.required_scenario_pack,
            "minimum_aggregate_status": self.minimum_aggregate_status,
            "allowed_aggregate_decisions": list(self.allowed_aggregate_decisions),
            "require_no_blockers": bool(self.require_no_blockers),
            "require_rollback_plan": bool(self.require_rollback_plan),
            "require_ci_handoff": bool(self.require_ci_handoff),
            "max_warning_count": int(self.max_warning_count),
            "max_error_count": int(self.max_error_count),
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


@dataclass
class PromotionRecommendation:
    recommendation_id: str
    profile_id: str
    target_environment: TargetEnvironment
    recommendation: PromotionDecision
    confidence: ConfidenceLevel
    reasons: List[str]
    blockers: List[str]
    warnings: List[str]
    rollback_precheck: Dict[str, Any]
    ci_handoff: Dict[str, Any]
    created_utc: str
    advisory_only: bool
    scenario_pack_id: str | None = None
    source_comparison_id: str | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recommendation_id": self.recommendation_id,
            "profile_id": self.profile_id,
            "target_environment": self.target_environment,
            "scenario_pack_id": self.scenario_pack_id,
            "source_comparison_id": self.source_comparison_id,
            "recommendation": self.recommendation,
            "confidence": self.confidence,
            "reasons": list(self.reasons),
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "rollback_precheck": dict(self.rollback_precheck),
            "ci_handoff": dict(self.ci_handoff),
            "created_utc": self.created_utc,
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


def validate_promotion_profile_dict(payload: Dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ValueError("PromotionProfile must be an object")
    _require_str(payload, "profile_id")
    _require_str(payload, "display_name")
    _require_str(payload, "required_scenario_pack")
    target_environment = _require_str(payload, "target_environment")
    if target_environment not in TARGET_ENVIRONMENTS:
        raise ValueError(f"invalid target_environment: {target_environment}")
    if not isinstance(payload.get("allowed_aggregate_decisions", []), list):
        raise ValueError("allowed_aggregate_decisions must be list")
    for key in (
        "require_no_blockers",
        "require_rollback_plan",
        "require_ci_handoff",
        "advisory_only",
    ):
        if not isinstance(payload.get(key), bool):
            raise ValueError(f"{key} must be bool")
    for key in ("max_warning_count", "max_error_count"):
        value = payload.get(key)
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{key} must be integer")
    if not isinstance(payload.get("metadata", {}), dict):
        raise ValueError("metadata must be dict")


def validate_promotion_recommendation_dict(payload: Dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ValueError("PromotionRecommendation must be an object")
    _require_str(payload, "recommendation_id")
    recommendation = _require_str(payload, "recommendation")
    if recommendation not in PROMOTION_DECISIONS:
        raise ValueError(f"invalid recommendation: {recommendation}")
    confidence = _require_str(payload, "confidence")
    if confidence not in CONFIDENCE_LEVELS:
        raise ValueError(f"invalid confidence: {confidence}")
    _require_str(payload, "created_utc")
    target_environment = _require_str(payload, "target_environment")
    if target_environment not in TARGET_ENVIRONMENTS:
        raise ValueError(f"invalid target_environment: {target_environment}")
    for key in ("reasons", "blockers", "warnings"):
        if not isinstance(payload.get(key, []), list):
            raise ValueError(f"{key} must be list")
    if not isinstance(payload.get("rollback_precheck", {}), dict):
        raise ValueError("rollback_precheck must be dict")
    if not isinstance(payload.get("ci_handoff", {}), dict):
        raise ValueError("ci_handoff must be dict")
    if not isinstance(payload.get("metadata", {}), dict):
        raise ValueError("metadata must be dict")


def _require_str(payload: Dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} required")
    return value

