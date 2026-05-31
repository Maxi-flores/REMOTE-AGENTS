from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from portfolio_orchestration.registry import load_portfolio_registry
from portfolio_roadmap.contracts import (
    PortfolioRoadmapItem,
    PortfolioRoadmapReport,
    PortfolioRoadmapWave,
    new_id,
    utc_now,
    validate_portfolio_roadmap_report_dict,
)
from portfolio_roadmap.sequencing import dependency_depth, horizon_for_priority, sequence_items, wave_for_horizon_and_depth


def load_json(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def generate_portfolio_roadmap_report(*, base_dir: str | Path = ".") -> Dict[str, Any]:
    root = Path(base_dir)
    registry = [record for record in load_portfolio_registry(base_dir=root) if isinstance(record, dict)]
    critical_path_report = load_json(root / ".control_plane" / "portfolio_critical_path" / "latest.json")
    dependency_report = load_json(root / ".control_plane" / "portfolio_dependencies" / "latest.json")
    portfolio_report = load_json(root / ".control_plane" / "portfolio" / "latest.json")
    onboarding_report = load_json(root / ".control_plane" / "portfolio_onboarding_recommendations" / "latest.json")
    progress_report = load_json(root / ".control_plane" / "portfolio_progress" / "latest.json")

    dependency_graph = dependency_report.get("dependency_graph")
    if not isinstance(dependency_graph, dict):
        dependency_graph = {}
    recommendations = critical_path_report.get("recommendations")
    if not isinstance(recommendations, list):
        recommendations = []
    onboarding_by_repo = _onboarding_priority_map(onboarding_report)
    status_map = _portfolio_status_map(portfolio_report)
    known_repo_ids = {str(r.get("repository_id") or "") for r in registry}

    roadmap_items: List[Dict[str, Any]] = []
    for rec in recommendations:
        if not isinstance(rec, dict):
            continue
        repository_id = str(rec.get("repository_id") or "").strip()
        if not repository_id:
            continue
        priority = str(rec.get("priority") or "P4")
        horizon = horizon_for_priority(priority)
        depth = dependency_depth(repository_id, dependency_graph)
        wave = wave_for_horizon_and_depth(horizon, depth)
        deps = dependency_graph.get(repository_id) if isinstance(dependency_graph.get(repository_id), list) else []
        onboarding_priority = onboarding_by_repo.get(repository_id, "P4")
        repo_status = str((status_map.get(repository_id) or {}).get("overall_status") or "unknown")
        if onboarding_priority in {"P0", "P1"} and horizon != "near_term":
            horizon = "near_term"
            wave = "wave_1"
        item = PortfolioRoadmapItem(
            item_id=new_id("roadmap_item"),
            source_recommendation_id=str(rec.get("recommendation_id") or new_id("rec_ref")),
            repository_id=repository_id,
            title=str(rec.get("title") or f"Roadmap action for {repository_id}"),
            objective=str(rec.get("recommended_action") or "Advance portfolio critical-path readiness."),
            priority=priority,
            horizon=horizon,
            wave=wave,
            dependencies=[str(dep) for dep in deps],
            expected_impact=str(rec.get("expected_portfolio_impact") or "Improves portfolio execution posture."),
            validation_focus=_validation_focus(priority, repo_status, onboarding_priority),
            advisory_only=True,
            metadata={
                "dependency_depth": depth,
                "repository_known_in_registry": repository_id in known_repo_ids,
                "onboarding_priority": onboarding_priority,
                "portfolio_status": repo_status,
            },
        ).to_dict()
        roadmap_items.append(item)

    if not roadmap_items:
        roadmap_items = _fallback_items(registry)

    ordered_items = sequence_items(roadmap_items)
    waves = _build_waves(ordered_items)
    milestones = _build_milestones(ordered_items, waves)
    report = PortfolioRoadmapReport(
        report_id=new_id("portfolio_roadmap_report"),
        generated_utc=utc_now(),
        source_critical_path_report_id=str(critical_path_report.get("report_id") or "missing_critical_path_report"),
        roadmap_items=ordered_items,
        waves=waves,
        milestones=milestones,
        recommended_sequence=[str(item.get("item_id")) for item in ordered_items],
        advisory_only=True,
        metadata={
            "advisory_only": True,
            "runtime_unchanged": True,
            "queue_mutation": False,
            "source_artifacts": {
                "portfolio_critical_path": str(root / ".control_plane" / "portfolio_critical_path" / "latest.json"),
                "portfolio_dependencies": str(root / ".control_plane" / "portfolio_dependencies" / "latest.json"),
                "portfolio": str(root / ".control_plane" / "portfolio" / "latest.json"),
                "portfolio_onboarding_recommendations": str(root / ".control_plane" / "portfolio_onboarding_recommendations" / "latest.json"),
            },
            "progress_summary": progress_report.get("portfolio_trends") if isinstance(progress_report.get("portfolio_trends"), dict) else {},
        },
    ).to_dict()
    validate_portfolio_roadmap_report_dict(report)
    return report


def _validation_focus(priority: str, overall_status: str, onboarding_priority: str) -> List[str]:
    checks = ["contract_validation", "advisory_artifact_refresh"]
    if priority in {"P0", "P1"}:
        checks.append("dependency_blocker_review")
    if overall_status in {"critical", "degraded"}:
        checks.append("readiness_recovery")
    if onboarding_priority in {"P0", "P1"}:
        checks.append("onboarding_blocker_resolution")
    return checks


def _build_waves(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    wave_map: Dict[str, List[str]] = {"wave_1": [], "wave_2": [], "wave_3": []}
    horizon_by_wave = {"wave_1": "near_term", "wave_2": "mid_term", "wave_3": "long_term"}
    for item in items:
        wave = str(item.get("wave") or "wave_3")
        if wave not in wave_map:
            wave = "wave_3"
        wave_map[wave].append(str(item.get("item_id") or ""))

    waves: List[Dict[str, Any]] = []
    titles = {
        "wave_1": "Near-Term Wave 1",
        "wave_2": "Mid-Term Wave 2",
        "wave_3": "Long-Term Wave 3",
    }
    objectives = {
        "wave_1": "Stabilize critical-path blockers and onboarding gaps.",
        "wave_2": "Expand readiness and portfolio intelligence coverage.",
        "wave_3": "Harden ecosystem governance and federation readiness.",
    }
    readiness_focus = {
        "wave_1": "P0/P1 execution readiness and dependency unblockers.",
        "wave_2": "P2 operational uplift and advisory baseline expansion.",
        "wave_3": "P3/P4 hardening and long-range portfolio coherence.",
    }
    risk_focus = {
        "wave_1": "Immediate high-risk dependency and governance bottlenecks.",
        "wave_2": "Medium-risk coordination and cross-repository consistency.",
        "wave_3": "Long-tail risk reduction and documentation maturity.",
    }
    for wave_id in ("wave_1", "wave_2", "wave_3"):
        waves.append(
            PortfolioRoadmapWave(
                wave_id=wave_id,
                title=titles[wave_id],
                horizon=horizon_by_wave[wave_id],
                objective=objectives[wave_id],
                items=[item_id for item_id in wave_map[wave_id] if item_id],
                readiness_focus=readiness_focus[wave_id],
                risk_focus=risk_focus[wave_id],
                advisory_only=True,
                metadata={},
            ).to_dict()
        )
    return waves


def _build_milestones(items: List[Dict[str, Any]], waves: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    milestones: List[Dict[str, Any]] = []
    for wave in waves:
        wave_id = str(wave.get("wave_id") or "wave")
        ids = list(wave.get("items") or [])
        milestones.append(
            {
                "milestone_id": new_id("roadmap_milestone"),
                "title": f"{str(wave.get('title') or wave_id)} completion",
                "description": f"Complete advisory objectives for {str(wave.get('title') or wave_id)}.",
                "horizon": str(wave.get("horizon") or "long_term"),
                "wave": wave_id,
                "item_ids": ids,
                "advisory_only": True,
                "metadata": {"item_count": len(ids)},
            }
        )
    if items:
        milestones.append(
            {
                "milestone_id": new_id("roadmap_milestone"),
                "title": "Portfolio strategic sequence baseline",
                "description": "Validated dependency-aware sequence for advisory portfolio execution.",
                "horizon": "near_term",
                "wave": "wave_1",
                "item_ids": [str(items[0].get("item_id"))],
                "advisory_only": True,
                "metadata": {"top_repository": str(items[0].get("repository_id") or "unknown")},
            }
        )
    return milestones


def _fallback_items(registry: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for idx, repo in enumerate(registry[:3], start=1):
        repository_id = str(repo.get("repository_id") or f"repo_{idx}")
        priority = "P1" if idx == 1 else ("P2" if idx == 2 else "P3")
        horizon = horizon_for_priority(priority)
        wave = "wave_1" if priority == "P1" else ("wave_2" if priority == "P2" else "wave_3")
        items.append(
            PortfolioRoadmapItem(
                item_id=new_id("roadmap_item"),
                source_recommendation_id="fallback_portfolio_recommendation",
                repository_id=repository_id,
                title=f"Portfolio roadmap baseline for {repository_id}",
                objective=f"Establish advisory execution baseline for {repository_id}.",
                priority=priority,
                horizon=horizon,
                wave=wave,
                dependencies=[],
                expected_impact="Improves portfolio-level visibility and sequencing readiness.",
                validation_focus=["contract_validation", "baseline_artifact_generation"],
                advisory_only=True,
                metadata={"fallback": True},
            ).to_dict()
        )
    return items


def _onboarding_priority_map(report: Dict[str, Any]) -> Dict[str, str]:
    recs = report.get("recommendations")
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
    for status in statuses:
        if not isinstance(status, dict):
            continue
        rid = str(status.get("repository_id") or "").strip()
        if rid:
            out[rid] = status
    return out
