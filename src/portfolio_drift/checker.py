from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Set

from portfolio_drift.contracts import PortfolioDriftFinding, new_id


def load_json(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except Exception:
        return None


def run_drift_checks(
    *,
    registry: Dict[str, Any],
    dependency_registry: Dict[str, Any],
    bootstrap_report: Dict[str, Any],
    onboarding_report: Dict[str, Any],
    dependency_report: Dict[str, Any],
    critical_path_report: Dict[str, Any],
    roadmap_report: Dict[str, Any],
    progress_report: Dict[str, Any],
    portfolio_report: Dict[str, Any],
) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    reg_ids = _registry_ids(registry)
    dep_sources, dep_targets = _dependency_ids(dependency_registry)
    enabled_registry = _enabled_registry_ids(registry)

    for rid in sorted(dep_sources | dep_targets):
        if rid not in reg_ids:
            findings.append(
                _finding(
                    severity="high",
                    drift_type="missing_registry_reference",
                    source_artifact="dependencies.json",
                    target_artifact="portfolio_registry.json",
                    repository_id=rid,
                    title=f"Dependency registry repository missing from portfolio registry: {rid}",
                    description=f"Repository '{rid}' appears in dependency registry but not in portfolio registry.",
                    action="Add missing repository to portfolio registry or remove invalid dependency reference.",
                )
            )
    for rid in sorted(enabled_registry):
        if rid not in dep_sources and rid not in dep_targets:
            findings.append(
                _finding(
                    severity="low",
                    drift_type="missing_dependency_reference",
                    source_artifact="portfolio_registry.json",
                    target_artifact="dependencies.json",
                    repository_id=rid,
                    title=f"Portfolio repository missing in dependency registry: {rid}",
                    description=f"Enabled repository '{rid}' has no dependency registry references.",
                    action="Add dependency mapping or explicitly mark repository as standalone.",
                )
            )

    bootstrap_records = _bootstrap_map(bootstrap_report)
    for rid in sorted(enabled_registry):
        if rid not in bootstrap_records:
            findings.append(
                _finding(
                    severity="medium",
                    drift_type="missing_bootstrap_record",
                    source_artifact="portfolio_registry.json",
                    target_artifact="portfolio_bootstrap/latest.json",
                    repository_id=rid,
                    title=f"Missing bootstrap record for enabled repository: {rid}",
                    description=f"Enabled repository '{rid}' has no onboarding/bootstrap record.",
                    action="Re-run portfolio bootstrap and validate onboarding coverage.",
                )
            )
    for rid in sorted(bootstrap_records.keys()):
        if rid not in reg_ids:
            findings.append(
                _finding(
                    severity="medium",
                    drift_type="missing_registry_reference",
                    source_artifact="portfolio_bootstrap/latest.json",
                    target_artifact="portfolio_registry.json",
                    repository_id=rid,
                    title=f"Bootstrap record references unknown repository: {rid}",
                    description=f"Bootstrap output includes repository '{rid}' not present in portfolio registry.",
                    action="Sync portfolio registry with bootstrap discovery results.",
                )
            )

    onboarding_recs = _onboarding_map(onboarding_report)
    for rid, record in bootstrap_records.items():
        artifact_status = str(record.get("artifact_status") or "").lower()
        rec = onboarding_recs.get(rid)
        if artifact_status == "none" and rec is None:
            findings.append(
                _finding(
                    severity="medium",
                    drift_type="stale_recommendation",
                    source_artifact="portfolio_bootstrap/latest.json",
                    target_artifact="portfolio_onboarding_recommendations/latest.json",
                    repository_id=rid,
                    title=f"Missing onboarding recommendation for artifact-free repository: {rid}",
                    description=f"Repository '{rid}' has artifact_status=none but no onboarding recommendation.",
                    action="Regenerate onboarding recommendations from latest bootstrap report.",
                )
            )
        if artifact_status == "complete" and rec and str(rec.get("priority") or "P4") in {"P0", "P1"}:
            findings.append(
                _finding(
                    severity="low",
                    drift_type="stale_recommendation",
                    source_artifact="portfolio_bootstrap/latest.json",
                    target_artifact="portfolio_onboarding_recommendations/latest.json",
                    repository_id=rid,
                    title=f"Potentially stale high-priority onboarding recommendation: {rid}",
                    description=f"Repository '{rid}' has artifact_status=complete but onboarding priority is {rec.get('priority')}.",
                    action="Review recommendation recency and downgrade if repository is now stable.",
                )
            )

    dep_high = {
        str(f.get("repository_id") or "")
        for f in dependency_report.get("findings", [])
        if isinstance(f, dict) and str(f.get("severity") or "").lower() in {"high", "critical"}
    }
    cp_recs = _critical_recommendation_map(critical_path_report)
    for rid in sorted(dep_high):
        if rid and rid not in cp_recs:
            findings.append(
                _finding(
                    severity="high",
                    drift_type="orphaned_critical_path_recommendation",
                    source_artifact="portfolio_dependencies/latest.json",
                    target_artifact="portfolio_critical_path/latest.json",
                    repository_id=rid,
                    title=f"High-severity dependency risk missing critical-path recommendation: {rid}",
                    description=f"Repository '{rid}' has high/critical dependency findings with no critical-path recommendation.",
                    action="Re-run critical path intelligence after dependency update.",
                )
            )
    for rid in sorted(cp_recs.keys()):
        if rid not in reg_ids:
            findings.append(
                _finding(
                    severity="high",
                    drift_type="orphaned_critical_path_recommendation",
                    source_artifact="portfolio_critical_path/latest.json",
                    target_artifact="portfolio_registry.json",
                    repository_id=rid,
                    title=f"Critical-path recommendation references unknown repository: {rid}",
                    description=f"Critical-path recommendation references '{rid}' which is absent from portfolio registry.",
                    action="Align critical-path outputs with current portfolio registry.",
                )
            )

    roadmap_items = roadmap_report.get("roadmap_items") if isinstance(roadmap_report.get("roadmap_items"), list) else []
    near_term_repo_ids = {
        str(item.get("repository_id") or "")
        for item in roadmap_items
        if isinstance(item, dict) and str(item.get("horizon") or "") == "near_term"
    }
    for rid, rec in cp_recs.items():
        priority = str(rec.get("priority") or "P4")
        if priority in {"P0", "P1"} and rid not in near_term_repo_ids:
            findings.append(
                _finding(
                    severity="medium",
                    drift_type="orphaned_roadmap_item",
                    source_artifact="portfolio_critical_path/latest.json",
                    target_artifact="portfolio_roadmap/latest.json",
                    repository_id=rid,
                    title=f"High-priority critical-path recommendation missing near-term roadmap item: {rid}",
                    description=f"P0/P1 critical-path recommendation for '{rid}' is not represented in near-term roadmap.",
                    action="Refresh roadmap planning from latest critical-path report.",
                )
            )
    for item in roadmap_items:
        if not isinstance(item, dict):
            continue
        rid = str(item.get("repository_id") or "")
        if rid and rid not in reg_ids:
            findings.append(
                _finding(
                    severity="high",
                    drift_type="orphaned_roadmap_item",
                    source_artifact="portfolio_roadmap/latest.json",
                    target_artifact="portfolio_registry.json",
                    repository_id=rid,
                    title=f"Roadmap item references unknown repository: {rid}",
                    description=f"Roadmap item references '{rid}' not present in portfolio registry.",
                    action="Sync roadmap items with current portfolio registry.",
                )
            )

    progress_metrics = progress_report.get("metrics") if isinstance(progress_report.get("metrics"), list) else []
    has_roadmap_count_metric = any(
        isinstance(m, dict) and str(m.get("repository_id") or "") == "portfolio" and str(m.get("metric_name") or "") == "roadmap_item_count"
        for m in progress_metrics
    )
    if roadmap_items and not has_roadmap_count_metric:
        findings.append(
            _finding(
                severity="medium",
                drift_type="missing_progress_metric",
                source_artifact="portfolio_roadmap/latest.json",
                target_artifact="portfolio_progress/latest.json",
                repository_id="portfolio",
                title="Roadmap count missing from progress metrics",
                description="Roadmap has items but progress report does not include roadmap_item_count metric.",
                action="Refresh portfolio progress report after roadmap export.",
            )
        )

    status_map = {
        str(s.get("repository_id") or ""): str(s.get("overall_status") or "unknown")
        for s in (portfolio_report.get("repository_statuses") if isinstance(portfolio_report.get("repository_statuses"), list) else [])
        if isinstance(s, dict)
    }
    for rid, status in status_map.items():
        cp = critical_path_report.get("critical_repository_scores") if isinstance(critical_path_report.get("critical_repository_scores"), list) else []
        cp_score = 0
        for score in cp:
            if isinstance(score, dict) and str(score.get("repository_id") or "") == rid:
                cp_score = int(score.get("critical_path_score") or 0)
                break
        if status == "healthy" and cp_score >= 75:
            findings.append(
                _finding(
                    severity="low",
                    drift_type="contradictory_status",
                    source_artifact="portfolio/latest.json",
                    target_artifact="portfolio_critical_path/latest.json",
                    repository_id=rid,
                    title=f"Potential status contradiction for {rid}",
                    description=f"Portfolio status is healthy while critical-path score is high ({cp_score}).",
                    action="Review scoring assumptions and refresh both portfolio and critical-path reports.",
                )
            )

    findings.extend(_stale_artifact_findings(bootstrap_report, onboarding_report, dependency_report, critical_path_report, roadmap_report, progress_report))
    return findings


def _stale_artifact_findings(
    bootstrap: Dict[str, Any],
    onboarding: Dict[str, Any],
    dependency: Dict[str, Any],
    critical_path: Dict[str, Any],
    roadmap: Dict[str, Any],
    progress: Dict[str, Any],
) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    # deterministic staleness threshold: any downstream older than upstream by > 5 minutes
    threshold_seconds = 300
    pairs = [
        ("portfolio_bootstrap/latest.json", bootstrap, "portfolio_onboarding_recommendations/latest.json", onboarding),
        ("portfolio_dependencies/latest.json", dependency, "portfolio_critical_path/latest.json", critical_path),
        ("portfolio_critical_path/latest.json", critical_path, "portfolio_roadmap/latest.json", roadmap),
        ("portfolio_roadmap/latest.json", roadmap, "portfolio_progress/latest.json", progress),
    ]
    for upstream_name, upstream_payload, downstream_name, downstream_payload in pairs:
        up = parse_utc(upstream_payload.get("generated_utc"))
        down = parse_utc(downstream_payload.get("generated_utc"))
        if not up or not down:
            continue
        drift = (up - down).total_seconds()
        if drift > threshold_seconds:
            findings.append(
                _finding(
                    severity="low",
                    drift_type="stale_artifact",
                    source_artifact=upstream_name,
                    target_artifact=downstream_name,
                    repository_id="portfolio",
                    title=f"Downstream artifact appears stale: {downstream_name}",
                    description=f"{downstream_name} is older than {upstream_name} by {int(drift)} seconds.",
                    action=f"Re-run {downstream_name} generator after refreshing {upstream_name}.",
                )
            )
    return findings


def _finding(
    *,
    severity: str,
    drift_type: str,
    source_artifact: str,
    target_artifact: str,
    repository_id: str,
    title: str,
    description: str,
    action: str,
) -> Dict[str, Any]:
    return PortfolioDriftFinding(
        finding_id=new_id("portfolio_drift_finding"),
        severity=severity,
        drift_type=drift_type,
        source_artifact=source_artifact,
        target_artifact=target_artifact,
        repository_id=repository_id or "portfolio",
        title=title,
        description=description,
        recommended_action=action,
        advisory_only=True,
        metadata={},
    ).to_dict()


def _registry_ids(registry: Dict[str, Any]) -> Set[str]:
    repos = registry.get("repositories")
    if not isinstance(repos, list):
        return set()
    return {str(r.get("repository_id") or "").strip() for r in repos if isinstance(r, dict) and str(r.get("repository_id") or "").strip()}


def _enabled_registry_ids(registry: Dict[str, Any]) -> Set[str]:
    repos = registry.get("repositories")
    if not isinstance(repos, list):
        return set()
    out: Set[str] = set()
    for repo in repos:
        if not isinstance(repo, dict):
            continue
        rid = str(repo.get("repository_id") or "").strip()
        if rid and bool(repo.get("enabled", True)):
            out.add(rid)
    return out


def _dependency_ids(dep_registry: Dict[str, Any]) -> tuple[Set[str], Set[str]]:
    deps = dep_registry.get("dependencies")
    if not isinstance(deps, list):
        return set(), set()
    src: Set[str] = set()
    tgt: Set[str] = set()
    for dep in deps:
        if not isinstance(dep, dict):
            continue
        rid = str(dep.get("repository_id") or "").strip()
        if rid:
            src.add(rid)
        depends_on = dep.get("depends_on")
        if isinstance(depends_on, list):
            for item in depends_on:
                sid = str(item).strip()
                if sid:
                    tgt.add(sid)
    return src, tgt


def _bootstrap_map(bootstrap: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    records = bootstrap.get("onboarding_records")
    if not isinstance(records, list):
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        rid = str(record.get("repository_id") or "").strip()
        if rid:
            out[rid] = record
    return out


def _onboarding_map(onboarding: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    recs = onboarding.get("recommendations")
    if not isinstance(recs, list):
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    for rec in recs:
        if not isinstance(rec, dict):
            continue
        rid = str(rec.get("repository_id") or "").strip()
        if rid:
            out[rid] = rec
    return out


def _critical_recommendation_map(critical_path: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    recs = critical_path.get("recommendations")
    if not isinstance(recs, list):
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    for rec in recs:
        if not isinstance(rec, dict):
            continue
        rid = str(rec.get("repository_id") or "").strip()
        if rid and rid not in out:
            out[rid] = rec
    return out

