from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from work_queue_manager.contracts import (
    WorkQueueItem,
    WorkQueueReport,
    new_id,
    utc_now,
    validate_work_queue_report_dict,
)
from work_queue_manager.dependency_graph import build_blockers, infer_dependencies, topological_order
from work_queue_manager.scoring import (
    compute_effort_score,
    compute_readiness_score,
    compute_risk_score,
    execution_readiness_from_score,
)


def load_refinement_report(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def generate_work_queue_report(
    *,
    refinement_report: Dict[str, Any] | None = None,
    refinement_report_path: str | Path | None = None,
    base_dir: str | Path = ".",
    limit: int | None = None,
) -> Dict[str, Any]:
    root = Path(base_dir)
    source_path = Path(refinement_report_path) if refinement_report_path else None
    if refinement_report is None:
        if source_path is None:
            source_path = root / ".control_plane" / "handoff_refinements" / "latest.json"
        refinement_report = load_refinement_report(source_path)

    refined_packages = refinement_report.get("refined_packages", []) if isinstance(refinement_report, dict) else []
    if not isinstance(refined_packages, list):
        refined_packages = []

    dependency_map = infer_dependencies([pkg for pkg in refined_packages if isinstance(pkg, dict)])
    known_ids = [str(pkg.get("refined_package_id")) for pkg in refined_packages if isinstance(pkg, dict)]
    blockers = build_blockers(dependency_map, known_ids)
    blocker_by_item = {str(b.get("queue_item_ref")): int(b.get("count") or 0) for b in blockers if isinstance(b, dict)}
    subsystem_counts = _subsystem_counts(refined_packages)

    queue_items: List[Dict[str, Any]] = []
    ordered_ids = topological_order(dependency_map)
    position_index = {pkg_id: idx + 1 for idx, pkg_id in enumerate(ordered_ids)}

    for pkg in refined_packages:
        if not isinstance(pkg, dict):
            continue
        pkg_id = str(pkg.get("refined_package_id") or "")
        effort = compute_effort_score(pkg)
        risk = compute_risk_score(pkg)
        dep_count = len(dependency_map.get(pkg_id, []))
        blocker_count = blocker_by_item.get(pkg_id, 0)
        subsystem = str(pkg.get("subsystem") or "system")
        readiness = compute_readiness_score(
            risk_score=risk,
            dependency_count=dep_count,
            blocker_count=blocker_count,
            effort_score=effort,
            subsystem_concentration=subsystem_counts.get(subsystem, 1),
        )
        queue_items.append(
            WorkQueueItem(
                queue_item_id=new_id("queue_item"),
                source_refined_package_id=pkg_id,
                title=str(pkg.get("title") or "Untitled"),
                subsystem=subsystem,
                priority=_derive_priority(readiness, risk),
                readiness_score=readiness,
                effort_score=effort,
                risk_score=risk,
                blocker_count=blocker_count,
                dependency_refs=list(dependency_map.get(pkg_id, [])),
                recommended_position=int(position_index.get(pkg_id, 9999)),
                execution_readiness=execution_readiness_from_score(readiness if blocker_count == 0 else min(readiness, 40)),
                advisory_only=True,
                metadata={"advisory_only": True, "source_batch_id": str(pkg.get("source_batch_id") or "")},
            ).to_dict()
        )

    queue_items = sorted(
        queue_items,
        key=lambda q: (
            int(q.get("recommended_position") or 9999),
            _priority_order(str(q.get("priority") or "P4")),
            -int(q.get("readiness_score") or 0),
        ),
    )
    for idx, item in enumerate(queue_items):
        item["recommended_position"] = idx + 1

    if isinstance(limit, int) and limit > 0:
        queue_items = queue_items[:limit]

    execution_order = [str(item.get("source_refined_package_id")) for item in queue_items]
    report = WorkQueueReport(
        report_id=new_id("work_queue_report"),
        generated_utc=utc_now(),
        queue_items=queue_items,
        dependency_graph={"dependencies": dependency_map},
        blockers=blockers,
        recommended_execution_order=execution_order,
        advisory_only=True,
        metadata={
            "advisory_only": True,
            "source_refinement_report_id": str(refinement_report.get("report_id") or "refinement_report_missing"),
            "source_report_path": str(source_path) if source_path else None,
            "base_dir": str(root),
        },
    ).to_dict()
    validate_work_queue_report_dict(report)
    return report


def _subsystem_counts(packages: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for pkg in packages:
        if not isinstance(pkg, dict):
            continue
        subsystem = str(pkg.get("subsystem") or "system")
        counts[subsystem] = counts.get(subsystem, 0) + 1
    return counts


def _derive_priority(readiness: int, risk: int) -> str:
    if risk >= 85:
        return "P0"
    if readiness >= 90:
        return "P1"
    if readiness >= 75:
        return "P1"
    if readiness >= 60:
        return "P2"
    if readiness >= 40:
        return "P3"
    return "P4"


def _priority_order(priority: str) -> int:
    return {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}.get(priority, 4)
