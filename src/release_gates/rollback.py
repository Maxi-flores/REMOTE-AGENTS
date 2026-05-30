from __future__ import annotations

from typing import Any, Dict, List


def summarize_rollback_requirements(target_environment: str) -> Dict[str, Any]:
    env = str(target_environment or "unknown")
    required_artifacts: List[str] = [
        "scenario_comparison.json",
        "release_readiness.json",
    ]
    recommended_steps = [
        "Identify last-known-good release artifact.",
        "Capture advisory blocker and warning context.",
        "Prepare rollback communication summary.",
    ]
    if env in {"staging", "production"}:
        required_artifacts.append("promotion_recommendations.json")
        recommended_steps.append("Confirm owner sign-off for rollback plan.")
    if env == "production":
        required_artifacts.append("gate_trace.json")
        recommended_steps.append("Prepare production rollback runbook checkpoint.")
    return {
        "target_environment": env,
        "required_artifacts": required_artifacts,
        "recommended_steps": recommended_steps,
    }


def build_rollback_precheck(comparison_result: Dict[str, Any], target_environment: str) -> Dict[str, Any]:
    baseline = summarize_rollback_requirements(target_environment)
    blockers = comparison_result.get("blockers", []) if isinstance(comparison_result, dict) else []
    aggregate = str((comparison_result or {}).get("aggregate_decision", "unknown"))
    missing_artifacts: List[str] = []
    rollback_required = aggregate in {"blocked", "mixed"} or (isinstance(blockers, list) and len(blockers) > 0)
    rollback_plan_status = "ready" if not rollback_required else "required"
    return {
        "target_environment": baseline["target_environment"],
        "rollback_required": rollback_required,
        "rollback_plan_status": rollback_plan_status,
        "required_artifacts": baseline["required_artifacts"],
        "missing_artifacts": missing_artifacts,
        "recommended_steps": baseline["recommended_steps"],
        "metadata": {"advisory_only": True},
    }

