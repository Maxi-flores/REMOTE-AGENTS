from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from release_gates.ci_handoff import build_ci_handoff_artifact
from release_gates.promotion_contracts import PromotionRecommendation, new_id, utc_now
from release_gates.promotion_loader import load_named_promotion_profile
from release_gates.rollback import build_rollback_precheck


STATUS_RANK = {
    "unknown": 0,
    "blocked": 1,
    "review_required": 2,
    "ready": 3,
}


def plan_promotion(comparison_result: Dict[str, Any], profile: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(comparison_result, dict) or not isinstance(profile, dict):
        return _unknown_recommendation("unknown profile or comparison payload")

    scenario_pack_id = _resolve_scenario_pack_id(comparison_result)
    aggregate_status = str(comparison_result.get("aggregate_status", "unknown"))
    aggregate_decision = str(comparison_result.get("aggregate_decision", "unknown"))
    blockers = _list_of_str(comparison_result.get("blockers"))
    warnings = _list_of_str(comparison_result.get("warnings"))
    warning_count = len(warnings)
    error_count = _estimate_error_count(comparison_result)
    reasons: List[str] = []
    decision = "promote"
    confidence = "high"
    recommendation_blockers: List[str] = []

    required_pack = str(profile.get("required_scenario_pack", ""))
    if required_pack and scenario_pack_id and required_pack != scenario_pack_id:
        recommendation_blockers.append(
            f"scenario pack mismatch: required={required_pack}, actual={scenario_pack_id}"
        )

    min_status = str(profile.get("minimum_aggregate_status", "unknown"))
    if STATUS_RANK.get(aggregate_status, -1) < STATUS_RANK.get(min_status, -1):
        recommendation_blockers.append(
            f"aggregate status below minimum: actual={aggregate_status}, minimum={min_status}"
        )

    allowed = [str(v) for v in profile.get("allowed_aggregate_decisions", []) if isinstance(v, str)]
    if aggregate_decision not in allowed:
        recommendation_blockers.append(
            f"aggregate decision not allowed: {aggregate_decision}"
        )

    if bool(profile.get("require_no_blockers", False)) and blockers:
        recommendation_blockers.append("scenario blockers present and profile requires none")

    max_warnings = int(profile.get("max_warning_count", 0))
    if warning_count > max_warnings:
        recommendation_blockers.append(
            f"warning count {warning_count} exceeds max {max_warnings}"
        )

    max_errors = int(profile.get("max_error_count", 0))
    if error_count > max_errors:
        recommendation_blockers.append(
            f"error count {error_count} exceeds max {max_errors}"
        )

    rollback_precheck = build_rollback_precheck(comparison_result, str(profile.get("target_environment", "unknown")))
    if bool(profile.get("require_rollback_plan", False)) and rollback_precheck.get("rollback_plan_status") not in {
        "ready",
        "required",
    }:
        recommendation_blockers.append("rollback precheck missing required planning metadata")

    provisional = {
        "target_environment": str(profile.get("target_environment", "unknown")),
        "recommendation": "hold",
    }
    ci_handoff = build_ci_handoff_artifact(provisional, comparison_result)
    if bool(profile.get("require_ci_handoff", False)) and not ci_handoff.get("recommended_checks"):
        recommendation_blockers.append("ci handoff metadata missing recommended checks")

    if recommendation_blockers:
        decision = "blocked"
        confidence = "high"
        reasons.extend(recommendation_blockers)
    else:
        if aggregate_status == "ready" and warning_count == 0:
            decision = "promote"
            confidence = "high"
            reasons.append("all promotion profile checks passed")
        elif aggregate_status in {"ready", "review_required"}:
            decision = "promote_with_warnings"
            confidence = "medium"
            reasons.append("promotion is advisory with warnings/review requirements")
        elif aggregate_status == "unknown":
            decision = "hold"
            confidence = "low"
            reasons.append("incomplete aggregate status for promotion")
        else:
            decision = "hold"
            confidence = "low"
            reasons.append("aggregate status requires manual review")

    recommendation = PromotionRecommendation(
        recommendation_id=new_id("promotion_recommendation"),
        profile_id=str(profile.get("profile_id", "unknown_profile")),
        target_environment=str(profile.get("target_environment", "dev")),  # type: ignore[arg-type]
        scenario_pack_id=scenario_pack_id,
        source_comparison_id=str(comparison_result.get("comparison_id")) if isinstance(comparison_result.get("comparison_id"), str) else None,
        recommendation=decision,  # type: ignore[arg-type]
        confidence=confidence,  # type: ignore[arg-type]
        reasons=reasons,
        blockers=recommendation_blockers,
        warnings=warnings,
        rollback_precheck=rollback_precheck,
        ci_handoff=build_ci_handoff_artifact(
            {
                "target_environment": str(profile.get("target_environment", "unknown")),
                "recommendation": decision,
            },
            comparison_result,
        ),
        created_utc=utc_now(),
        advisory_only=bool(profile.get("advisory_only", True)),
        metadata={"advisory_only": bool(profile.get("advisory_only", True)), "error_count": error_count},
    )
    return recommendation.to_dict()


def plan_promotion_from_scenario_report(
    path: str | Path = ".release_reports/scenario_comparison.json",
    profile_name: str = "dev_promotion_profile",
) -> Dict[str, Any]:
    report_path = Path(path)
    if not report_path.exists():
        return _unknown_recommendation("scenario report missing")
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    comparison = payload.get("comparison", payload) if isinstance(payload, dict) else {}
    if not isinstance(comparison, dict):
        return _unknown_recommendation("scenario comparison malformed")
    profile = load_named_promotion_profile(profile_name)
    return plan_promotion(comparison, profile)


def explain_promotion_recommendation(recommendation: Dict[str, Any]) -> str:
    decision = str(recommendation.get("recommendation", "unknown"))
    env = str(recommendation.get("target_environment", "unknown"))
    blockers = len(recommendation.get("blockers", [])) if isinstance(recommendation.get("blockers"), list) else 0
    warnings = len(recommendation.get("warnings", [])) if isinstance(recommendation.get("warnings"), list) else 0
    return f"{env}: {decision}; blockers={blockers}; warnings={warnings}"


def _resolve_scenario_pack_id(comparison_result: Dict[str, Any]) -> str | None:
    scenario_pack_id = comparison_result.get("scenario_pack_id")
    if isinstance(scenario_pack_id, str) and scenario_pack_id.strip():
        return scenario_pack_id
    return None


def _estimate_error_count(comparison_result: Dict[str, Any]) -> int:
    summary = comparison_result.get("summary", {})
    if isinstance(summary, dict):
        decision_counts = summary.get("decision_counts", {})
        if isinstance(decision_counts, dict):
            blocked = decision_counts.get("blocked", 0)
            if isinstance(blocked, int):
                return max(0, blocked)
    decisions = comparison_result.get("policy_decisions", [])
    if isinstance(decisions, list):
        return sum(
            1
            for entry in decisions
            if isinstance(entry, dict)
            and isinstance(entry.get("decision"), dict)
            and str(entry.get("decision", {}).get("decision")) == "blocked"
        )
    return 0


def _list_of_str(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(v) for v in value if isinstance(v, str)]


def _unknown_recommendation(reason: str) -> Dict[str, Any]:
    recommendation = PromotionRecommendation(
        recommendation_id=new_id("promotion_recommendation"),
        profile_id="unknown_profile",
        target_environment="dev",
        scenario_pack_id=None,
        source_comparison_id=None,
        recommendation="unknown",
        confidence="low",
        reasons=[reason],
        blockers=[],
        warnings=[],
        rollback_precheck={"target_environment": "unknown", "metadata": {"advisory_only": True}},
        ci_handoff={"target_environment": "unknown", "metadata": {"advisory_only": True}},
        created_utc=utc_now(),
        advisory_only=True,
        metadata={"advisory_only": True},
    )
    return recommendation.to_dict()

