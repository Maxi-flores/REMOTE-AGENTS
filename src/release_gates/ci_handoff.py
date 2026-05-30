from __future__ import annotations

from typing import Any, Dict


def summarize_ci_requirements(target_environment: str) -> Dict[str, Any]:
    env = str(target_environment or "unknown")
    checks = ["unit-tests", "contract-validation", "advisory-release-gates"]
    stage = "ci-dev"
    if env == "staging":
        checks += ["integration-tests", "scenario-comparison-check"]
        stage = "ci-staging"
    elif env == "production":
        checks += ["integration-tests", "scenario-comparison-check", "rollback-precheck"]
        stage = "ci-production"
    return {
        "target_environment": env,
        "recommended_checks": checks,
        "required_artifacts": ["release_readiness.json", "scenario_comparison.json"],
        "suggested_pipeline_stage": stage,
    }


def build_ci_handoff_artifact(recommendation: Dict[str, Any], comparison_result: Dict[str, Any]) -> Dict[str, Any]:
    env = str(recommendation.get("target_environment", "unknown"))
    baseline = summarize_ci_requirements(env)
    return {
        "target_environment": env,
        "recommended_checks": baseline["recommended_checks"],
        "required_artifacts": baseline["required_artifacts"],
        "suggested_pipeline_stage": baseline["suggested_pipeline_stage"],
        "advisory_gate_decision": comparison_result.get("aggregate_decision", "unknown"),
        "promotion_recommendation": recommendation.get("recommendation", "unknown"),
        "metadata": {"advisory_only": True},
    }

