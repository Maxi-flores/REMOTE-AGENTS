from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from portfolio_onboarding_recommendations.contracts import (
    PortfolioOnboardingRecommendationReport,
    RepositoryOnboardingRecommendation,
    new_id,
    utc_now,
    validate_portfolio_onboarding_recommendation_report_dict,
)


def load_json(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def generate_portfolio_onboarding_recommendation_report(
    *,
    base_dir: str | Path = ".",
    bootstrap_report: Dict[str, Any] | None = None,
    bootstrap_report_path: str | Path | None = None,
) -> Dict[str, Any]:
    root = Path(base_dir)
    if bootstrap_report is None:
        path = Path(bootstrap_report_path) if bootstrap_report_path else (root / ".control_plane" / "portfolio_bootstrap" / "latest.json")
        bootstrap_report = load_json(path)
    records = bootstrap_report.get("onboarding_records") if isinstance(bootstrap_report.get("onboarding_records"), list) else []

    recommendations: List[Dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        recommendations.append(_recommendation_from_record(record))
    recommendations = sorted(recommendations, key=lambda r: (_priority_order(str(r.get("priority") or "P4")), str(r.get("repository_id") or "")))
    report = PortfolioOnboardingRecommendationReport(
        report_id=new_id("portfolio_onboarding_recommendation_report"),
        generated_utc=utc_now(),
        source_bootstrap_report_id=str(bootstrap_report.get("report_id") or "portfolio_bootstrap_report_missing"),
        recommendations=recommendations,
        summary=_summary(recommendations),
        advisory_only=True,
        metadata={
            "advisory_only": True,
            "runtime_unchanged": True,
            "queue_mutation": False,
        },
    ).to_dict()
    validate_portfolio_onboarding_recommendation_report_dict(report)
    return report


def _recommendation_from_record(record: Dict[str, Any]) -> Dict[str, Any]:
    repository_id = str(record.get("repository_id") or "unknown")
    repository_name = str(record.get("repository_name") or repository_id)
    repository_path = str(record.get("repository_path") or ".")
    onboarding_state = str(record.get("onboarding_state") or "discovered")
    artifact_status = str(record.get("artifact_status") or "unknown")
    discovered = bool(record.get("discovered"))

    if (not discovered and onboarding_state == "registered") or artifact_status == "unknown":
        priority = "P1"
        risk_level = "high"
        title = f"{repository_name} repository not discovered at configured path"
        actions = [
            "Verify configured repository path.",
            "Confirm repository exists locally.",
            "Update portfolio registry if path is wrong.",
            "Run portfolio bootstrap again.",
        ]
        validations = [
            "python src/portfolio_bootstrap/cli.py --print",
            "python src/portfolio_bootstrap/cli.py --export",
        ]
    elif discovered and artifact_status == "none":
        priority = "P1"
        risk_level = "high"
        title = f"{repository_name} repository discovered but advisory artifacts are missing"
        actions = [
            "Run repository intelligence baseline inside that repository or configure external artifact import.",
            "Generate advisory baseline artifacts for work queue and execution dossier flows.",
            "Do not mutate repository automatically; keep onboarding manual and reviewed.",
        ]
        validations = [
            "python src/portfolio_bootstrap/cli.py --print",
            "python src/portfolio_orchestration/cli.py --print",
        ]
    elif discovered and artifact_status == "partial":
        priority = "P2"
        risk_level = "medium"
        title = f"{repository_name} repository has partial advisory artifact coverage"
        actions = [
            "Generate missing advisory layers.",
            "Prioritize repository intelligence and execution dossier baseline coverage.",
            "Re-run bootstrap and portfolio reports to confirm coverage improvements.",
        ]
        validations = [
            "python src/portfolio_bootstrap/cli.py --print",
            "python src/portfolio_orchestration/cli.py --print",
        ]
    else:
        priority = "P3"
        risk_level = "low"
        title = f"{repository_name} repository onboarding is complete"
        actions = [
            "Continue periodic portfolio bootstrap refresh.",
            "Monitor advisory artifact freshness.",
        ]
        validations = [
            "python src/portfolio_bootstrap/cli.py --print",
        ]

    return RepositoryOnboardingRecommendation(
        recommendation_id=new_id("repo_onboarding_recommendation"),
        repository_id=repository_id,
        repository_name=repository_name,
        repository_path=repository_path,
        onboarding_state=onboarding_state,
        artifact_status=artifact_status,
        priority=priority,
        title=title,
        recommended_actions=actions,
        validation_commands=validations,
        risk_level=risk_level,
        advisory_only=True,
        metadata={"discovered": discovered},
    ).to_dict()


def _summary(recommendations: List[Dict[str, Any]]) -> Dict[str, Any]:
    priority_counts: Dict[str, int] = {}
    risk_counts: Dict[str, int] = {}
    for item in recommendations:
        if not isinstance(item, dict):
            continue
        p = str(item.get("priority") or "P4")
        r = str(item.get("risk_level") or "low")
        priority_counts[p] = priority_counts.get(p, 0) + 1
        risk_counts[r] = risk_counts.get(r, 0) + 1
    return {
        "recommendation_count": len(recommendations),
        "priority_counts": priority_counts,
        "risk_counts": risk_counts,
    }


def _priority_order(value: str) -> int:
    order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}
    return order.get(value, 4)

