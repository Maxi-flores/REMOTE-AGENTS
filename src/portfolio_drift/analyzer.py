from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from portfolio_drift.checker import load_json, run_drift_checks
from portfolio_drift.contracts import PortfolioDriftReport, new_id, utc_now, validate_portfolio_drift_report_dict


def generate_portfolio_drift_report(*, base_dir: str | Path = ".") -> Dict[str, Any]:
    root = Path(base_dir)
    registry = load_json(root / ".config" / "portfolio" / "portfolio_registry.json")
    dependency_registry = load_json(root / ".config" / "portfolio" / "dependencies.json")
    bootstrap_report = load_json(root / ".control_plane" / "portfolio_bootstrap" / "latest.json")
    onboarding_report = load_json(root / ".control_plane" / "portfolio_onboarding_recommendations" / "latest.json")
    dependency_report = load_json(root / ".control_plane" / "portfolio_dependencies" / "latest.json")
    critical_path_report = load_json(root / ".control_plane" / "portfolio_critical_path" / "latest.json")
    roadmap_report = load_json(root / ".control_plane" / "portfolio_roadmap" / "latest.json")
    progress_report = load_json(root / ".control_plane" / "portfolio_progress" / "latest.json")
    portfolio_report = load_json(root / ".control_plane" / "portfolio" / "latest.json")

    findings = run_drift_checks(
        registry=registry,
        dependency_registry=dependency_registry,
        bootstrap_report=bootstrap_report,
        onboarding_report=onboarding_report,
        dependency_report=dependency_report,
        critical_path_report=critical_path_report,
        roadmap_report=roadmap_report,
        progress_report=progress_report,
        portfolio_report=portfolio_report,
    )
    summary = _summary(findings)
    report = PortfolioDriftReport(
        report_id=new_id("portfolio_drift_report"),
        generated_utc=utc_now(),
        findings=findings,
        summary=summary,
        advisory_only=True,
        metadata={
            "advisory_only": True,
            "runtime_unchanged": True,
            "queue_mutation": False,
            "source_artifacts": {
                "registry": str(root / ".config" / "portfolio" / "portfolio_registry.json"),
                "dependency_registry": str(root / ".config" / "portfolio" / "dependencies.json"),
                "bootstrap": str(root / ".control_plane" / "portfolio_bootstrap" / "latest.json"),
                "onboarding": str(root / ".control_plane" / "portfolio_onboarding_recommendations" / "latest.json"),
                "dependencies": str(root / ".control_plane" / "portfolio_dependencies" / "latest.json"),
                "critical_path": str(root / ".control_plane" / "portfolio_critical_path" / "latest.json"),
                "roadmap": str(root / ".control_plane" / "portfolio_roadmap" / "latest.json"),
                "progress": str(root / ".control_plane" / "portfolio_progress" / "latest.json"),
                "portfolio": str(root / ".control_plane" / "portfolio" / "latest.json"),
            },
        },
    ).to_dict()
    validate_portfolio_drift_report_dict(report)
    return report


def _summary(findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    sev_counts: Dict[str, int] = {"info": 0, "low": 0, "medium": 0, "high": 0, "critical": 0}
    drift_counts: Dict[str, int] = {}
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        sev = str(finding.get("severity") or "info")
        if sev in sev_counts:
            sev_counts[sev] += 1
        drift = str(finding.get("drift_type") or "unknown")
        drift_counts[drift] = drift_counts.get(drift, 0) + 1
    return {
        "finding_count": len(findings),
        "severity_counts": sev_counts,
        "drift_type_counts": drift_counts,
    }

