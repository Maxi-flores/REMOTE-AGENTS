from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Set

from portfolio_dependencies.contracts import (
    DependencyFinding,
    DependencyGraphReport,
    new_id,
    utc_now,
    validate_dependency_graph_report_dict,
)
from portfolio_dependencies.graph import build_consumers_map, build_dependency_chains, build_dependency_graph
from portfolio_dependencies.registry import load_dependency_registry
from portfolio_orchestration.registry import load_portfolio_registry


def load_json(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def generate_dependency_graph_report(*, base_dir: str | Path = ".") -> Dict[str, Any]:
    root = Path(base_dir)
    portfolio_repos = load_portfolio_registry(base_dir=root)
    portfolio_ids = {str(r.get("repository_id") or "") for r in portfolio_repos if isinstance(r, dict)}
    dep_records = load_dependency_registry(base_dir=root)
    dep_graph = build_dependency_graph(dep_records)
    chains = build_dependency_chains(dep_graph)
    consumers = build_consumers_map(dep_graph)

    bootstrap = load_json(root / ".control_plane" / "portfolio_bootstrap" / "latest.json")
    onboarding = load_json(root / ".control_plane" / "portfolio_onboarding_recommendations" / "latest.json")
    portfolio_report = load_json(root / ".control_plane" / "portfolio" / "latest.json")

    readiness_map = _readiness_map(bootstrap)
    onboarding_priority_map = _onboarding_priority_map(onboarding)
    portfolio_status_map = _portfolio_status_map(portfolio_report)

    findings: List[Dict[str, Any]] = []
    for repo, deps in dep_graph.items():
        for dep in deps:
            if dep not in portfolio_ids:
                findings.append(
                    _finding(
                        severity="high",
                        repository_id=repo,
                        dependency_repository_id=dep,
                        category="dependency_unknown",
                        title=f"{repo} depends on unknown repository {dep}",
                        description=f"Dependency target '{dep}' is not present in portfolio registry.",
                        impact="Dependency planning cannot validate onboarding/readiness for this dependency.",
                        recommended_action=f"Add {dep} to portfolio registry or remove it from dependency mapping.",
                    )
                )
                continue
            dep_readiness = readiness_map.get(dep, 0)
            dep_state = str((portfolio_status_map.get(dep) or {}).get("overall_status") or "unknown")
            dep_onboarding_priority = onboarding_priority_map.get(dep, "P4")
            if dep_readiness < 50 or dep_state in {"critical", "degraded"}:
                findings.append(
                    _finding(
                        severity="high",
                        repository_id=repo,
                        dependency_repository_id=dep,
                        category="dependency_blocked",
                        title=f"{repo} inherits dependency blocker from {dep}",
                        description=f"Dependency '{dep}' readiness/state is below threshold (readiness={dep_readiness}, status={dep_state}).",
                        impact=f"{repo} delivery planning is blocked by dependency readiness.",
                        recommended_action=f"Raise {dep} readiness before scheduling dependent portfolio work for {repo}.",
                    )
                )
            if dep_onboarding_priority in {"P0", "P1"}:
                findings.append(
                    _finding(
                        severity="medium",
                        repository_id=repo,
                        dependency_repository_id=dep,
                        category="dependency_risk",
                        title=f"{repo} inherits onboarding risk from {dep}",
                        description=f"Dependency '{dep}' has high-priority onboarding recommendations ({dep_onboarding_priority}).",
                        impact=f"{repo} risk posture inherits upstream onboarding gaps.",
                        recommended_action=f"Prioritize onboarding recommendations for {dep} before dependent work.",
                    )
                )
            if dep_readiness == 0 and dep in portfolio_ids:
                findings.append(
                    _finding(
                        severity="medium",
                        repository_id=repo,
                        dependency_repository_id=dep,
                        category="dependency_missing",
                        title=f"{repo} dependency {dep} has missing readiness baseline",
                        description=f"Dependency '{dep}' has no usable readiness baseline yet.",
                        impact="Dependency chain confidence is reduced.",
                        recommended_action=f"Generate/bootstrap advisory readiness for {dep}.",
                    )
                )

    for chain in chains:
        if len(chain) < 2:
            continue
        findings.append(
            _finding(
                severity="info",
                repository_id=chain[0],
                dependency_repository_id=chain[-1],
                category="dependency_chain",
                title=f"Dependency chain detected: {' -> '.join(chain)}",
                description=f"Chain length {len(chain)} across portfolio repositories.",
                impact="Longer chains increase coordination complexity.",
                recommended_action="Review chain and prioritize upstream readiness improvements.",
                metadata={"chain": chain},
            )
        )

    impact = {
        "repository_count": len(portfolio_ids),
        "dependency_count": sum(len(v) for v in dep_graph.values()),
        "consumer_count": sum(len(v) for v in consumers.values()),
        "finding_count": len(findings),
        "severity_counts": _severity_counts(findings),
    }
    report = DependencyGraphReport(
        report_id=new_id("portfolio_dependency_report"),
        generated_utc=utc_now(),
        dependency_graph=dep_graph,
        dependency_chains=chains,
        findings=findings,
        portfolio_impact=impact,
        advisory_only=True,
        metadata={"advisory_only": True, "runtime_unchanged": True, "queue_mutation": False},
    ).to_dict()
    validate_dependency_graph_report_dict(report)
    return report


def _finding(
    *,
    severity: str,
    repository_id: str,
    dependency_repository_id: str,
    category: str,
    title: str,
    description: str,
    impact: str,
    recommended_action: str,
    metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    return DependencyFinding(
        finding_id=new_id("dependency_finding"),
        severity=severity,
        repository_id=repository_id,
        dependency_repository_id=dependency_repository_id,
        category=category,
        title=title,
        description=description,
        impact=impact,
        recommended_action=recommended_action,
        metadata=dict(metadata or {}),
    ).to_dict()


def _readiness_map(bootstrap: Dict[str, Any]) -> Dict[str, int]:
    records = bootstrap.get("onboarding_records")
    if not isinstance(records, list):
        return {}
    out: Dict[str, int] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        rid = str(record.get("repository_id") or "").strip()
        if rid:
            out[rid] = int(record.get("readiness_estimate") or 0)
    return out


def _onboarding_priority_map(onboarding: Dict[str, Any]) -> Dict[str, str]:
    recs = onboarding.get("recommendations")
    if not isinstance(recs, list):
        return {}
    out: Dict[str, str] = {}
    for rec in recs:
        if not isinstance(rec, dict):
            continue
        rid = str(rec.get("repository_id") or "").strip()
        if rid:
            out[rid] = str(rec.get("priority") or "P4")
    return out


def _portfolio_status_map(report: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    statuses = report.get("repository_statuses")
    if not isinstance(statuses, list):
        return {}
    out: Dict[str, Dict[str, Any]] = {}
    for item in statuses:
        if not isinstance(item, dict):
            continue
        rid = str(item.get("repository_id") or "").strip()
        if rid:
            out[rid] = item
    return out


def _severity_counts(findings: List[Dict[str, Any]]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        sev = str(finding.get("severity") or "info")
        out[sev] = out.get(sev, 0) + 1
    return out

