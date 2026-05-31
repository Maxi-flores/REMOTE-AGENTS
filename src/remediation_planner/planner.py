from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from remediation_planner.contracts import (
    RemediationBatch,
    RemediationItem,
    RemediationPlanReport,
    new_id,
    utc_now,
    validate_remediation_plan_report_dict,
)
from remediation_planner.scoring import derive_priority, rank_item, score_finding


def load_repository_intelligence_report(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def generate_remediation_plan_report(
    *,
    rie_report: Dict[str, Any] | None = None,
    rie_report_path: str | Path | None = None,
    base_dir: str | Path = ".",
    limit: int | None = None,
) -> Dict[str, Any]:
    root = Path(base_dir)
    source_path = Path(rie_report_path) if rie_report_path else None
    if rie_report is None:
        if source_path is None:
            latest = root / ".control_plane" / "repository_intelligence" / "latest.json"
            source_path = latest if latest.exists() else (root / ".control_plane" / "repository_intelligence" / "repository_intelligence_report.json")
        rie_report = load_repository_intelligence_report(source_path)
    findings = rie_report.get("findings", []) if isinstance(rie_report, dict) else []
    items = _build_items(findings, repository_name=str(rie_report.get("repository_name") or root.resolve().name))
    items = sorted(items, key=lambda item: (_priority_order(str(item.get("priority") or "P4")), -rank_item(item), str(item.get("title") or "")))
    if isinstance(limit, int) and limit > 0:
        items = items[:limit]
    batches = _build_batches(items)
    sequence = [batch["batch_id"] for batch in batches]
    summary = {
        "item_count": len(items),
        "batch_count": len(batches),
        "priority_counts": _counts(items, "priority"),
        "category_counts": _counts(items, "category"),
        "source_report_status": str(rie_report.get("overall_status") or "unknown"),
    }
    report = RemediationPlanReport(
        report_id=new_id("remediation_report"),
        generated_utc=utc_now(),
        source_report_id=str(rie_report.get("report_id") or "repository_intelligence_report_missing"),
        overall_status=_overall_status(items),
        items=items,
        batches=batches,
        recommended_sequence=sequence,
        summary=summary,
        advisory_only=True,
        metadata={
            "advisory_only": True,
            "source_report_path": str(source_path) if source_path else None,
            "base_dir": str(root),
            "queue_mutation": False,
            "auto_enqueue": False,
        },
    ).to_dict()
    validate_remediation_plan_report_dict(report)
    return report


def _build_items(findings: Any, *, repository_name: str) -> List[Dict[str, Any]]:
    if not isinstance(findings, list) or not findings:
        return [_continuity_item(repository_name)]
    out: List[Dict[str, Any]] = []
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        severity = str(finding.get("severity") or "info").lower()
        if severity == "info":
            continue
        scores = score_finding(finding)
        category = _map_category(str(finding.get("category") or "observability"))
        item = RemediationItem(
            item_id=new_id("remediation_item"),
            title=str(finding.get("title") or "Repository remediation task"),
            description=str(finding.get("description") or "Advisory remediation item generated from repository intelligence."),
            category=category,
            priority=derive_priority(
                risk_score=scores["risk_score"],
                effort_score=scores["effort_score"],
                confidence_score=scores["confidence_score"],
            ),
            status="open",
            repository=repository_name,
            source_finding_ids=[str(finding.get("finding_id") or new_id("finding_ref"))],
            suggested_action=str(finding.get("recommended_action") or "Review finding and define remediation steps."),
            risk_score=scores["risk_score"],
            effort_score=scores["effort_score"],
            confidence_score=scores["confidence_score"],
            advisory_only=True,
            metadata={"severity": severity, "source": "repository_intelligence"},
        ).to_dict()
        out.append(item)
    return out if out else [_continuity_item(repository_name)]


def _continuity_item(repository_name: str) -> Dict[str, Any]:
    return RemediationItem(
        item_id=new_id("remediation_item"),
        title="Repository intelligence continuity refresh",
        description="No actionable high-severity findings were present. Keep remediation baseline fresh with periodic reviews.",
        category="observability",
        priority="P3",
        status="planned",
        repository=repository_name,
        source_finding_ids=[],
        suggested_action="Re-run repository intelligence analysis and track drift in findings across snapshots.",
        risk_score=45,
        effort_score=25,
        confidence_score=85,
        advisory_only=True,
        metadata={"source": "healthy_continuity"},
    ).to_dict()


def _build_batches(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for item in items:
        grouped.setdefault(str(item.get("priority") or "P4"), []).append(item)
    out: List[Dict[str, Any]] = []
    for priority in ("P0", "P1", "P2", "P3", "P4"):
        chunk = grouped.get(priority, [])
        if not chunk:
            continue
        out.append(
            RemediationBatch(
                batch_id=new_id("remediation_batch"),
                name=f"{priority} remediation batch",
                priority=priority,
                status="planned" if priority in {"P0", "P1", "P2"} else "ready",
                repository=str(chunk[0].get("repository") or "unknown"),
                item_ids=[str(item["item_id"]) for item in chunk],
                estimated_total_effort=sum(int(item.get("effort_score") or 0) for item in chunk),
                expected_risk_reduction=sum(int(item.get("risk_score") or 0) for item in chunk),
                advisory_only=True,
                metadata={"item_count": len(chunk)},
            ).to_dict()
        )
    return out


def _map_category(category: str) -> str:
    value = category.strip().lower()
    allowed = {"config", "docs", "tests", "runtime", "contracts", "governance", "lifecycle", "release"}
    if value in allowed:
        return value
    if value == "documentation":
        return "docs"
    if value == "testing":
        return "tests"
    return "observability"


def _priority_order(priority: str) -> int:
    order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}
    return order.get(priority, 4)


def _counts(items: List[Dict[str, Any]], key: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for item in items:
        value = str(item.get(key) or "unknown")
        counts[value] = counts.get(value, 0) + 1
    return counts


def _overall_status(items: List[Dict[str, Any]]) -> str:
    if not items:
        return "healthy"
    if any(str(item.get("priority")) == "P0" for item in items):
        return "blocked"
    if any(str(item.get("priority")) == "P1" for item in items):
        return "degraded"
    if any(str(item.get("priority")) == "P2" for item in items):
        return "warning"
    return "healthy"
