from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from strategic_missions.contracts import StrategicMissionCandidate, StrategicMissionReport, new_id, utc_now, validate_strategic_mission_report_dict
from strategic_missions.scoring import derive_priority, rank_candidate, score_finding


def load_executive_briefing(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def generate_strategic_mission_report(
    *,
    briefing: Dict[str, Any] | None = None,
    briefing_path: str | Path | None = None,
    base_dir: str | Path = ".",
    limit: int | None = None,
) -> Dict[str, Any]:
    root = Path(base_dir)
    repo_intel = load_executive_briefing(root / ".control_plane" / "repository_intelligence" / "repository_intelligence_report.json")
    remediation_plan = load_executive_briefing(root / ".control_plane" / "remediation_plans" / "remediation_plan_report.json")
    remediation_handoff = load_executive_briefing(root / ".control_plane" / "remediation_handoffs" / "latest.json")
    if briefing is None:
        source_path = Path(briefing_path) if briefing_path else (root / ".control_plane" / "executive" / "executive_briefing.json")
        briefing = load_executive_briefing(source_path)
    else:
        source_path = Path(briefing_path) if briefing_path else None

    candidates = _candidates_from_briefing(
        briefing or {},
        repository_intelligence_report=repo_intel,
        remediation_plan_report=remediation_plan,
        remediation_handoff_report=remediation_handoff,
    )
    if limit is not None and isinstance(limit, int) and limit > 0:
        candidates = candidates[:limit]

    sequence = [c["candidate_id"] for c in candidates]
    summary = {
        "candidate_count": len(candidates),
        "priorities": _priority_counts(candidates),
        "categories": _category_counts(candidates),
        "source_overall_status": str((briefing or {}).get("overall_status") or "unknown"),
    }
    report = StrategicMissionReport(
        report_id=new_id("strategic_mission_report"),
        generated_utc=utc_now(),
        overall_status=_overall_status(candidates),
        candidates=candidates,
        recommended_sequence=sequence,
        summary=summary,
        advisory_only=True,
        metadata={
            "advisory_only": True,
            "source_briefing_path": str(source_path) if source_path else None,
            "base_dir": str(root),
            "auto_enqueue": False,
            "queue_mutation": False,
        },
    ).to_dict()
    validate_strategic_mission_report_dict(report)
    return report


def render_strategic_mission_report_text(report: Dict[str, Any]) -> str:
    lines = ["Strategic Mission Recommendations", ""]
    candidates = report.get("candidates", []) if isinstance(report.get("candidates"), list) else []
    if not candidates:
        lines.append("No recommendations available.")
    else:
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            lines.append(f"{candidate.get('priority', 'P4')}: {candidate.get('title', 'Untitled')}")
    return "\n".join(lines).strip() + "\n"


def _candidates_from_briefing(
    briefing: Dict[str, Any],
    *,
    repository_intelligence_report: Dict[str, Any] | None = None,
    remediation_plan_report: Dict[str, Any] | None = None,
    remediation_handoff_report: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    if not isinstance(briefing, dict):
        return _maintenance_candidates()
    findings = briefing.get("top_risks")
    actions = briefing.get("recommended_actions")
    repo_candidates = _candidates_from_repo_intel(repository_intelligence_report or {})
    remediation_candidates = _candidates_from_remediation(remediation_plan_report or {})
    handoff_candidates = _candidates_from_handoffs(remediation_handoff_report or {})
    if isinstance(findings, list) and findings:
        base = [_candidate_from_finding(f, actions) for f in findings if isinstance(f, dict)]
        return _rank_candidates(base + repo_candidates + remediation_candidates + handoff_candidates)
    # healthy/no-risks => maintenance continuity recommendations
    return _rank_candidates(_maintenance_candidates() + repo_candidates + remediation_candidates + handoff_candidates)


def _candidate_from_finding(finding: Dict[str, Any], actions: Any) -> Dict[str, Any]:
    finding_id = str(finding.get("finding_id") or new_id("finding_ref"))
    title = str(finding.get("title") or "Resolve advisory finding")
    category = _safe_category(str(finding.get("category") or "system"))
    scores = score_finding(finding)
    priority = derive_priority(**scores)
    repo = _repo_hint_from_text(f"{finding.get('title', '')} {finding.get('description', '')}")
    suggested_instruction = _suggested_instruction(title=title, category=category, actions=actions)
    candidate = StrategicMissionCandidate(
        candidate_id=new_id("strategic_mission"),
        title=title,
        description=str(finding.get("description") or title),
        source_finding_ids=[finding_id],
        category=category,
        priority=priority,
        risk_reduction_score=scores["risk_reduction_score"],
        effort_score=scores["effort_score"],
        confidence_score=scores["confidence_score"],
        recommended_repository=repo,
        suggested_instruction=suggested_instruction,
        advisory_only=True,
        metadata={"source": "executive_briefing", "severity": finding.get("severity", "info")},
    ).to_dict()
    return candidate


def _maintenance_candidates() -> List[Dict[str, Any]]:
    templates = [
        {
            "title": "Lifecycle continuity refresh",
            "description": "Review lifecycle capability coverage and refresh advisory lifecycle health summaries.",
            "category": "lifecycle",
            "suggested_instruction": "Run lifecycle coverage review and summarize any drift in advisory capability profiles.",
            "risk_reduction_score": 50,
            "effort_score": 30,
            "confidence_score": 85,
        },
        {
            "title": "Release readiness continuity baseline",
            "description": "Regenerate release readiness artifacts and verify advisory report continuity.",
            "category": "release",
            "suggested_instruction": "Regenerate release readiness report and document any advisory drift findings.",
            "risk_reduction_score": 55,
            "effort_score": 35,
            "confidence_score": 85,
        },
        {
            "title": "Memory graph ingestion coverage sweep",
            "description": "Audit optional mission-to-memory-graph ingestion coverage and note gaps.",
            "category": "memory",
            "suggested_instruction": "Audit memory graph ingestion paths and summarize uncovered mission metadata.",
            "risk_reduction_score": 45,
            "effort_score": 40,
            "confidence_score": 80,
        },
    ]
    out: List[Dict[str, Any]] = []
    for item in templates:
        priority = derive_priority(
            risk_reduction_score=int(item["risk_reduction_score"]),
            effort_score=int(item["effort_score"]),
            confidence_score=int(item["confidence_score"]),
        )
        out.append(
            StrategicMissionCandidate(
                candidate_id=new_id("strategic_mission"),
                title=str(item["title"]),
                description=str(item["description"]),
                source_finding_ids=[],
                category=str(item["category"]),
                priority=priority,
                risk_reduction_score=int(item["risk_reduction_score"]),
                effort_score=int(item["effort_score"]),
                confidence_score=int(item["confidence_score"]),
                recommended_repository=None,
                suggested_instruction=str(item["suggested_instruction"]),
                advisory_only=True,
                metadata={"source": "healthy_continuity"},
            ).to_dict()
        )
    return out


def _candidates_from_repo_intel(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(report, dict) or not report:
        return []
    findings = report.get("findings")
    if not isinstance(findings, list):
        return []
    out: List[Dict[str, Any]] = []
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        sev = str(finding.get("severity") or "info").lower()
        if sev not in {"high", "critical", "medium"}:
            continue
        category = _safe_category(str(finding.get("category") or "repository"))
        scores = score_finding({"severity": sev, "category": category})
        priority = derive_priority(**scores)
        title = str(finding.get("title") or "Repository intelligence improvement")
        out.append(
            StrategicMissionCandidate(
                candidate_id=new_id("strategic_mission"),
                title=title,
                description=str(finding.get("description") or title),
                source_finding_ids=[str(finding.get("finding_id") or new_id("finding_ref"))],
                category=category,
                priority=priority,
                risk_reduction_score=scores["risk_reduction_score"],
                effort_score=scores["effort_score"],
                confidence_score=scores["confidence_score"],
                recommended_repository=_repo_hint_from_paths(finding.get("path_refs")),
                suggested_instruction=str(
                    finding.get("recommended_action")
                    or f"Address repository intelligence finding: {title}."
                ),
                advisory_only=True,
                metadata={"source": "repository_intelligence", "severity": sev},
            ).to_dict()
        )
    return out


def _candidates_from_remediation(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(report, dict) or not report:
        return []
    batches = report.get("batches")
    if not isinstance(batches, list):
        return []
    out: List[Dict[str, Any]] = []
    for batch in batches[:3]:
        if not isinstance(batch, dict):
            continue
        priority = str(batch.get("priority") or "P4")
        if priority not in {"P0", "P1", "P2"}:
            continue
        title = str(batch.get("name") or "Remediation batch")
        out.append(
            StrategicMissionCandidate(
                candidate_id=new_id("strategic_mission"),
                title=f"Execute advisory {title}",
                description=f"Convert remediation batch '{title}' into tracked strategic mission work.",
                source_finding_ids=[str(batch.get("batch_id") or new_id("batch_ref"))],
                category="repository",
                priority=priority,
                risk_reduction_score=min(95, int(batch.get("expected_risk_reduction") or 60)),
                effort_score=min(90, int(batch.get("estimated_total_effort") or 45)),
                confidence_score=85,
                recommended_repository=(str(batch.get("repository") or "").strip() or None),
                suggested_instruction=f"Create advisory mission for remediation batch '{title}' and track items: {', '.join(batch.get('item_ids', [])[:5])}.",
                advisory_only=True,
                metadata={"source": "remediation_plan"},
            ).to_dict()
        )
    return out


def _candidates_from_handoffs(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(report, dict) or not report:
        return []
    packages = report.get("packages")
    if not isinstance(packages, list):
        return []
    out: List[Dict[str, Any]] = []
    for package in packages[:3]:
        if not isinstance(package, dict):
            continue
        source_batch = str(package.get("source_batch_id") or "")
        title = str(package.get("title") or "Implementation package")
        out.append(
            StrategicMissionCandidate(
                candidate_id=new_id("strategic_mission"),
                title=f"Review and execute package: {title}",
                description="Move a prepared implementation package through human review and manual execution.",
                source_finding_ids=[source_batch] if source_batch else [],
                category="repository",
                priority="P2",
                risk_reduction_score=70,
                effort_score=45,
                confidence_score=85,
                recommended_repository=str((package.get("metadata") or {}).get("repository") or "").strip() or None,
                suggested_instruction=f"Review implementation package '{title}', validate scope, then execute manually after approval.",
                advisory_only=True,
                metadata={"source": "remediation_handoff"},
            ).to_dict()
        )
    return out


def _suggested_instruction(*, title: str, category: str, actions: Any) -> str:
    action_hint = ""
    if isinstance(actions, list):
        for action in actions:
            if isinstance(action, str) and action.strip():
                action_hint = action.strip()
                break
    if action_hint:
        return f"{action_hint} (Strategic focus: {category}; context: {title})"
    return f"Address strategic {category} finding: {title}."


def _safe_category(value: str) -> str:
    value = value.strip().lower()
    allowed = {"lifecycle", "governance", "release", "memory", "scheduler", "tooling", "repository", "system"}
    if value in allowed:
        return value
    if value == "mission":
        return "system"
    return "system"


def _repo_hint_from_text(text: str) -> str | None:
    # deterministic light heuristic only
    lowered = text.lower()
    for repo in ("powerframe", "powerstarter", "conceptshop", "therockettree", "pf-wai"):
        if repo in lowered:
            return repo
    return None


def _repo_hint_from_paths(path_refs: Any) -> str | None:
    if not isinstance(path_refs, list):
        return None
    joined = " ".join(str(p) for p in path_refs if isinstance(p, str)).lower()
    return _repo_hint_from_text(joined)


def _rank_candidates(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        candidates,
        key=lambda c: (
            _priority_order(str(c.get("priority") or "P4")),
            -rank_candidate(c),
            str(c.get("title") or ""),
        ),
    )


def _priority_order(priority: str) -> int:
    order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}
    return order.get(priority, 4)


def _priority_counts(candidates: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for c in candidates:
        p = str(c.get("priority") or "P4")
        counts[p] = counts.get(p, 0) + 1
    return counts


def _category_counts(candidates: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for c in candidates:
        cat = str(c.get("category") or "system")
        counts[cat] = counts.get(cat, 0) + 1
    return counts


def _overall_status(candidates: List[Dict[str, Any]]) -> str:
    if not candidates:
        return "healthy"
    if any(str(c.get("priority")) == "P0" for c in candidates):
        return "blocked"
    if any(str(c.get("priority")) == "P1" for c in candidates):
        return "degraded"
    if any(str(c.get("priority")) == "P2" for c in candidates):
        return "warning"
    return "healthy"
