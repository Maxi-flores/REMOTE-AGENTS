from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal


ComparisonStrategy = Literal["compare_all", "strictest_wins", "permissive_preview", "production_candidate"]
AggregateDecision = Literal["pass", "pass_with_warnings", "blocked", "mixed", "unknown"]
AggregateStatus = Literal["ready", "review_required", "blocked", "unknown"]

COMPARISON_STRATEGIES = {"compare_all", "strictest_wins", "permissive_preview", "production_candidate"}
AGGREGATE_DECISIONS = {"pass", "pass_with_warnings", "blocked", "mixed", "unknown"}
AGGREGATE_STATUSES = {"ready", "review_required", "blocked", "unknown"}


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


@dataclass
class ScenarioPack:
    scenario_pack_id: str
    display_name: str
    policy_names: List[str]
    comparison_strategy: ComparisonStrategy
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_pack_id": self.scenario_pack_id,
            "display_name": self.display_name,
            "policy_names": list(self.policy_names),
            "comparison_strategy": self.comparison_strategy,
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


@dataclass
class ScenarioComparisonResult:
    comparison_id: str
    scenario_pack_id: str
    generated_utc: str
    comparison_strategy: ComparisonStrategy
    policy_decisions: List[Dict[str, Any]]
    aggregate_decision: AggregateDecision
    aggregate_status: AggregateStatus
    blockers: List[str]
    warnings: List[str]
    summary: Dict[str, Any]
    advisory_only: bool
    report_id: str | None = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "comparison_id": self.comparison_id,
            "scenario_pack_id": self.scenario_pack_id,
            "report_id": self.report_id,
            "generated_utc": self.generated_utc,
            "comparison_strategy": self.comparison_strategy,
            "policy_decisions": list(self.policy_decisions),
            "aggregate_decision": self.aggregate_decision,
            "aggregate_status": self.aggregate_status,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "summary": dict(self.summary),
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


def validate_scenario_pack_dict(payload: Dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ValueError("ScenarioPack must be an object")
    _require_str(payload, "scenario_pack_id")
    _require_str(payload, "display_name")
    strategy = _require_str(payload, "comparison_strategy")
    if strategy not in COMPARISON_STRATEGIES:
        raise ValueError(f"invalid comparison_strategy: {strategy}")
    if not isinstance(payload.get("policy_names", []), list):
        raise ValueError("policy_names must be list")
    if not isinstance(payload.get("advisory_only"), bool):
        raise ValueError("advisory_only must be bool")
    if not isinstance(payload.get("metadata", {}), dict):
        raise ValueError("metadata must be dict")


def validate_scenario_comparison_result_dict(payload: Dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ValueError("ScenarioComparisonResult must be an object")
    _require_str(payload, "comparison_id")
    _require_str(payload, "generated_utc")
    if not isinstance(payload.get("policy_decisions", []), list):
        raise ValueError("policy_decisions must be list")
    decision = _require_str(payload, "aggregate_decision")
    if decision not in AGGREGATE_DECISIONS:
        raise ValueError(f"invalid aggregate_decision: {decision}")
    status = _require_str(payload, "aggregate_status")
    if status not in AGGREGATE_STATUSES:
        raise ValueError(f"invalid aggregate_status: {status}")
    for key in ("blockers", "warnings"):
        if not isinstance(payload.get(key, []), list):
            raise ValueError(f"{key} must be lists")
    if not isinstance(payload.get("summary", {}), dict):
        raise ValueError("summary must be dict")


def _require_str(payload: Dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} required")
    return value

