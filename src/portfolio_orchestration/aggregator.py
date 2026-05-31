from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from portfolio_orchestration.contracts import (
    PortfolioExecutiveFinding,
    PortfolioReport,
    PortfolioRepositoryStatus,
    new_id,
    utc_now,
    validate_portfolio_report_dict,
)
from portfolio_orchestration.registry import load_portfolio_registry
from portfolio_orchestration.scoring import execution_order, score_portfolio, score_repository_status


def load_json(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def generate_portfolio_report(*, base_dir: str | Path = ".", registry_path: str | Path | None = None) -> Dict[str, Any]:
    root = Path(base_dir)
    repositories = load_portfolio_registry(registry_path, base_dir=root)
    statuses: List[Dict[str, Any]] = []
    findings: List[Dict[str, Any]] = []

    intel = load_json(root / ".control_plane" / "repository_intelligence" / "repository_intelligence_report.json")
    remediation = load_json(root / ".control_plane" / "remediation_plans" / "remediation_plan_report.json")
    queue = load_json(root / ".control_plane" / "work_queue" / "latest.json")
    dossiers = load_json(root / ".control_plane" / "execution_dossiers" / "latest.json")
    bootstrap = load_json(root / ".control_plane" / "portfolio_bootstrap" / "latest.json")
    onboarding_recommendations = load_json(root / ".control_plane" / "portfolio_onboarding_recommendations" / "latest.json")
    dependency_report = load_json(root / ".control_plane" / "portfolio_dependencies" / "latest.json")
    critical_path_report = load_json(root / ".control_plane" / "portfolio_critical_path" / "latest.json")
    roadmap_report = load_json(root / ".control_plane" / "portfolio_roadmap" / "latest.json")
    progress_report = load_json(root / ".control_plane" / "portfolio_progress" / "latest.json")
    drift_report = load_json(root / ".control_plane" / "portfolio_drift" / "latest.json")
    bootstrap_index = _bootstrap_index(bootstrap)

    for repo in repositories:
        if not isinstance(repo, dict):
            continue
        repo_id = str(repo.get("repository_id") or repo.get("repository_name") or "unknown")
        remediation_count = _count_remediation(remediation, repo_id)
        queue_count, queue_ready_avg = _count_queue(queue, repo_id)
        dossier_count, dossier_readiness_avg, high_risk_dossier_count = _count_dossiers(dossiers, repo_id)
        intel_findings = _count_intelligence_findings(intel, repo_id)
        bootstrap_readiness = int((bootstrap_index.get(repo_id) or {}).get("readiness_estimate") or 0)
        bootstrap_artifact_status = str((bootstrap_index.get(repo_id) or {}).get("artifact_status") or "unknown")

        readiness = _normalize_readiness(queue_ready_avg, dossier_readiness_avg, queue_count, dossier_count, bootstrap_readiness)
        health, readiness, overall = score_repository_status(
            remediation_count=remediation_count,
            queue_count=queue_count,
            dossier_count=dossier_count,
            readiness_score=readiness,
            intelligence_finding_count=intel_findings,
            high_risk_dossier_count=high_risk_dossier_count,
        )

        statuses.append(
            PortfolioRepositoryStatus(
                repository_id=repo_id,
                health_score=health,
                remediation_count=remediation_count,
                queue_count=queue_count,
                dossier_count=dossier_count,
                readiness_score=readiness,
                overall_status=overall,
                metadata={
                    "repository_name": repo.get("repository_name"),
                    "high_risk_dossier_count": high_risk_dossier_count,
                    "repository_intelligence_findings": intel_findings,
                    "bootstrap_artifact_status": bootstrap_artifact_status,
                },
            ).to_dict()
        )

        findings.extend(
            _build_findings(
                repository_id=repo_id,
                repository_name=str(repo.get("repository_name") or repo_id),
                remediation_count=remediation_count,
                queue_count=queue_count,
                dossier_count=dossier_count,
                readiness=readiness,
                intel_findings=intel_findings,
                high_risk_dossier_count=high_risk_dossier_count,
                bootstrap_artifact_status=bootstrap_artifact_status,
            )
        )

    health_score, readiness_score = score_portfolio(statuses)
    onboarding_summary = onboarding_recommendations.get("summary") if isinstance(onboarding_recommendations.get("summary"), dict) else {}
    dependency_summary = dependency_report.get("portfolio_impact") if isinstance(dependency_report.get("portfolio_impact"), dict) else {}
    critical_path_summary = critical_path_report.get("portfolio_leverage_summary") if isinstance(critical_path_report.get("portfolio_leverage_summary"), dict) else {}
    roadmap_items = roadmap_report.get("roadmap_items") if isinstance(roadmap_report.get("roadmap_items"), list) else []
    roadmap_waves = roadmap_report.get("waves") if isinstance(roadmap_report.get("waves"), list) else []
    progress_trends = progress_report.get("portfolio_trends") if isinstance(progress_report.get("portfolio_trends"), dict) else {}
    drift_summary = drift_report.get("summary") if isinstance(drift_report.get("summary"), dict) else {}
    if onboarding_summary:
        findings.append(
            PortfolioExecutiveFinding(
                finding_id=new_id("portfolio_finding"),
                severity="low",
                category="onboarding",
                repository_id="portfolio",
                title="Portfolio onboarding recommendation summary available",
                description=f"{int(onboarding_summary.get('recommendation_count') or 0)} onboarding recommendation(s) generated.",
                recommended_action="Use onboarding recommendations to improve repository discovery and advisory artifact coverage.",
            ).to_dict()
        )
    if dependency_summary:
        findings.append(
            PortfolioExecutiveFinding(
                finding_id=new_id("portfolio_finding"),
                severity="medium" if int(dependency_summary.get("finding_count") or 0) > 0 else "low",
                category="dependencies",
                repository_id="portfolio",
                title="Portfolio dependency intelligence summary available",
                description=f"{int(dependency_summary.get('finding_count') or 0)} dependency finding(s) detected.",
                recommended_action="Use dependency findings to sequence onboarding and readiness work across repositories.",
            ).to_dict()
        )
    if critical_path_summary:
        findings.append(
            PortfolioExecutiveFinding(
                finding_id=new_id("portfolio_finding"),
                severity="low",
                category="critical_path",
                repository_id="portfolio",
                title="Portfolio critical path summary available",
                description=f"{int(critical_path_summary.get('recommendation_count') or 0)} critical-path recommendation(s) generated.",
                recommended_action="Use critical-path recommendations to prioritize highest-leverage repository actions.",
            ).to_dict()
        )
    if roadmap_items or roadmap_waves:
        findings.append(
            PortfolioExecutiveFinding(
                finding_id=new_id("portfolio_finding"),
                severity="low",
                category="roadmap",
                repository_id="portfolio",
                title="Portfolio strategic roadmap summary available",
                description=f"{len(roadmap_items)} roadmap item(s) grouped into {len(roadmap_waves)} wave(s).",
                recommended_action="Use roadmap waves to align near/mid/long-term advisory portfolio execution planning.",
            ).to_dict()
        )
    if progress_trends:
        findings.append(
            PortfolioExecutiveFinding(
                finding_id=new_id("portfolio_finding"),
                severity="low",
                category="progress",
                repository_id="portfolio",
                title="Portfolio progress trend summary available",
                description=f"Overall progress trend is {str(progress_trends.get('overall_trend') or 'unknown')}.",
                recommended_action="Use progress trends to verify whether advisory execution posture is improving over time.",
            ).to_dict()
        )
    if drift_summary:
        findings.append(
            PortfolioExecutiveFinding(
                finding_id=new_id("portfolio_finding"),
                severity="medium" if int(drift_summary.get("finding_count") or 0) > 0 else "low",
                category="drift",
                repository_id="portfolio",
                title="Portfolio drift summary available",
                description=f"{int(drift_summary.get('finding_count') or 0)} drift finding(s) detected.",
                recommended_action="Use drift intelligence to reconcile portfolio artifact inconsistencies.",
            ).to_dict()
        )
    report = PortfolioReport(
        report_id=new_id("portfolio_report"),
        generated_utc=utc_now(),
        repositories=repositories,
        repository_statuses=statuses,
        findings=findings,
        portfolio_health_score=health_score,
        portfolio_readiness_score=readiness_score,
        recommended_execution_order=execution_order(statuses),
        advisory_only=True,
        metadata={
            "advisory_only": True,
            "runtime_unchanged": True,
            "queue_mutation": False,
            "source_artifacts": {
                "repository_intelligence": str(root / ".control_plane" / "repository_intelligence" / "repository_intelligence_report.json"),
                "remediation_plans": str(root / ".control_plane" / "remediation_plans" / "remediation_plan_report.json"),
                "work_queue": str(root / ".control_plane" / "work_queue" / "latest.json"),
                "execution_dossiers": str(root / ".control_plane" / "execution_dossiers" / "latest.json"),
                "portfolio_bootstrap": str(root / ".control_plane" / "portfolio_bootstrap" / "latest.json"),
                "portfolio_onboarding_recommendations": str(root / ".control_plane" / "portfolio_onboarding_recommendations" / "latest.json"),
                "portfolio_dependencies": str(root / ".control_plane" / "portfolio_dependencies" / "latest.json"),
                "portfolio_critical_path": str(root / ".control_plane" / "portfolio_critical_path" / "latest.json"),
                "portfolio_roadmap": str(root / ".control_plane" / "portfolio_roadmap" / "latest.json"),
                "portfolio_progress": str(root / ".control_plane" / "portfolio_progress" / "latest.json"),
                "portfolio_drift": str(root / ".control_plane" / "portfolio_drift" / "latest.json"),
            },
            "onboarding_recommendation_summary": onboarding_summary,
            "dependency_summary": dependency_summary,
            "critical_path_summary": critical_path_summary,
            "roadmap_summary": {
                "roadmap_item_count": len(roadmap_items),
                "wave_count": len(roadmap_waves),
                "source_report_id": str(roadmap_report.get("report_id") or ""),
            },
            "progress_summary": progress_trends,
            "drift_summary": drift_summary,
        },
    ).to_dict()
    validate_portfolio_report_dict(report)
    return report


def _count_remediation(report: Dict[str, Any], repository_id: str) -> int:
    items = report.get("items")
    if not isinstance(items, list):
        return 0
    rid = repository_id.lower()
    count = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        repo_name = str(item.get("repository_name") or item.get("repository") or "").lower()
        if repo_name and (rid in repo_name or repo_name in rid):
            count += 1
    return count


def _count_queue(report: Dict[str, Any], repository_id: str) -> tuple[int, int]:
    items = report.get("queue_items")
    if not isinstance(items, list):
        return 0, 0
    rid = repository_id.lower()
    matched = []
    for item in items:
        if not isinstance(item, dict):
            continue
        meta = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
        repo_name = str(meta.get("repository") or meta.get("repository_name") or "").lower()
        if repo_name and (rid in repo_name or repo_name in rid):
            matched.append(int(item.get("readiness_score") or 0))
    if not matched:
        return 0, 0
    return len(matched), int(sum(matched) / len(matched))


def _count_dossiers(report: Dict[str, Any], repository_id: str) -> tuple[int, int, int]:
    dossiers = report.get("dossiers")
    if not isinstance(dossiers, list):
        return 0, 0, 0
    rid = repository_id.lower()
    readiness_vals: List[int] = []
    high_risk = 0
    for dossier in dossiers:
        if not isinstance(dossier, dict):
            continue
        meta = dossier.get("metadata") if isinstance(dossier.get("metadata"), dict) else {}
        repo_name = str(meta.get("repository") or meta.get("repository_name") or "").lower()
        if repo_name and (rid in repo_name or repo_name in rid):
            readiness_vals.append(int(dossier.get("execution_readiness_score") or 0))
            risk = str(dossier.get("execution_risk") or "medium").lower()
            if risk in {"high", "critical"}:
                high_risk += 1
    if not readiness_vals:
        return 0, 0, 0
    return len(readiness_vals), int(sum(readiness_vals) / len(readiness_vals)), high_risk


def _count_intelligence_findings(report: Dict[str, Any], repository_id: str) -> int:
    findings = report.get("findings")
    if not isinstance(findings, list):
        return 0
    rid = repository_id.lower()
    total = 0
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        paths = finding.get("path_refs")
        if not isinstance(paths, list):
            continue
        joined = " ".join(str(p).lower() for p in paths if isinstance(p, str))
        if rid and rid in joined:
            total += 1
    return total


def _normalize_readiness(queue_avg: int, dossier_avg: int, queue_count: int, dossier_count: int, bootstrap_readiness: int) -> int:
    vals: List[int] = []
    if queue_count > 0:
        vals.append(max(0, min(100, int(queue_avg))))
    if dossier_count > 0:
        vals.append(max(0, min(100, int(dossier_avg))))
    if bootstrap_readiness > 0:
        vals.append(max(0, min(100, int(bootstrap_readiness))))
    if not vals:
        return 0
    return int(sum(vals) / len(vals))


def _build_findings(
    *,
    repository_id: str,
    repository_name: str,
    remediation_count: int,
    queue_count: int,
    dossier_count: int,
    readiness: int,
    intel_findings: int,
    high_risk_dossier_count: int,
    bootstrap_artifact_status: str,
) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    if intel_findings == 0:
        findings.append(
            PortfolioExecutiveFinding(
                finding_id=new_id("portfolio_finding"),
                severity="medium",
                category="repository_intelligence",
                repository_id=repository_id,
                title=f"{repository_name} missing repository intelligence coverage",
                description="No repository intelligence findings matched this repository.",
                recommended_action=f"Run repository intelligence export for {repository_name}.",
            ).to_dict()
        )
    if remediation_count >= 8:
        findings.append(
            PortfolioExecutiveFinding(
                finding_id=new_id("portfolio_finding"),
                severity="high",
                category="remediation",
                repository_id=repository_id,
                title=f"{repository_name} has high remediation backlog",
                description=f"{remediation_count} remediation items are associated with this repository.",
                recommended_action="Prioritize top remediation batches and convert to execution dossiers.",
            ).to_dict()
        )
    if queue_count > 0 and dossier_count == 0:
        findings.append(
            PortfolioExecutiveFinding(
                finding_id=new_id("portfolio_finding"),
                severity="high",
                category="execution",
                repository_id=repository_id,
                title=f"{repository_name} has queue items but no execution dossiers",
                description=f"{queue_count} queue items exist with no corresponding execution dossiers.",
                recommended_action="Generate execution readiness dossiers for queued items.",
            ).to_dict()
        )
    if readiness < 60:
        findings.append(
            PortfolioExecutiveFinding(
                finding_id=new_id("portfolio_finding"),
                severity="medium",
                category="readiness",
                repository_id=repository_id,
                title=f"{repository_name} readiness score is low",
                description=f"Repository readiness score is {readiness}.",
                recommended_action="Improve readiness by reducing blockers and increasing validated dossier coverage.",
            ).to_dict()
        )
    if high_risk_dossier_count > 0:
        findings.append(
            PortfolioExecutiveFinding(
                finding_id=new_id("portfolio_finding"),
                severity="medium",
                category="risk",
                repository_id=repository_id,
                title=f"{repository_name} has high-risk implementation backlog",
                description=f"{high_risk_dossier_count} high-risk dossier(s) detected.",
                recommended_action="Review high-risk dossiers and split scope where feasible before execution.",
            ).to_dict()
        )
    if bootstrap_artifact_status in {"none", "partial"}:
        findings.append(
            PortfolioExecutiveFinding(
                finding_id=new_id("portfolio_finding"),
                severity="medium" if bootstrap_artifact_status == "none" else "low",
                category="onboarding",
                repository_id=repository_id,
                title=f"{repository_name} onboarding artifacts are {bootstrap_artifact_status}",
                description="Portfolio bootstrap report indicates onboarding artifact coverage is incomplete.",
                recommended_action=f"Use portfolio bootstrap onboarding to improve advisory artifact coverage for {repository_name}.",
            ).to_dict()
        )
    return findings


def _bootstrap_index(report: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    records = report.get("onboarding_records")
    if not isinstance(records, list):
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        repo_id = str(record.get("repository_id") or "").strip()
        if repo_id:
            out[repo_id] = record
    return out
