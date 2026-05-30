from __future__ import annotations

from typing import Any, Dict, List

from release_center.timeline_contracts import ReleaseMilestone, new_id


def milestone_from_readiness_event(event: Dict[str, Any]) -> Dict[str, Any]:
    return _make_milestone(
        title="Readiness Milestone",
        description=str(event.get("description", "Readiness evaluation")),
        milestone_type="readiness",
        status=_milestone_status_from_event(event),
        owner="Release Owner",
        event=event,
    )


def milestone_from_gate_event(event: Dict[str, Any]) -> Dict[str, Any]:
    return _make_milestone(
        title="Gate Simulation Milestone",
        description=str(event.get("description", "Gate simulation completed")),
        milestone_type="gate",
        status=_milestone_status_from_event(event),
        owner="Governance Owner",
        event=event,
    )


def milestone_from_scenario_event(event: Dict[str, Any]) -> Dict[str, Any]:
    return _make_milestone(
        title="Scenario Comparison Milestone",
        description=str(event.get("description", "Scenario comparison completed")),
        milestone_type="scenario",
        status=_milestone_status_from_event(event),
        owner="Platform Owner",
        event=event,
    )


def milestones_from_promotion_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for event in events:
        if str(event.get("event_type")) == "promotion_recommendation":
            env = str(event.get("related_environment", "unknown"))
            owner = "Repository Owner" if env == "dev" else "Release Owner"
            if env == "staging":
                owner = "Governance Owner"
            if env == "production":
                owner = "Release Owner"
            out.append(
                _make_milestone(
                    title=f"{env.title()} Promotion Milestone",
                    description=str(event.get("description", "")),
                    milestone_type="promotion",
                    status=_milestone_status_from_event(event),
                    owner=owner,
                    event=event,
                    target_environment=env,
                )
            )
        elif str(event.get("event_type")) == "rollback_precheck":
            out.append(
                _make_milestone(
                    title=f"{str(event.get('related_environment', 'unknown')).title()} Rollback Milestone",
                    description=str(event.get("description", "")),
                    milestone_type="rollback",
                    status=_milestone_status_from_event(event),
                    owner="Rollback Owner",
                    event=event,
                    target_environment=str(event.get("related_environment", "unknown")),
                )
            )
        elif str(event.get("event_type")) == "ci_handoff":
            out.append(
                _make_milestone(
                    title=f"{str(event.get('related_environment', 'unknown')).title()} CI Handoff Milestone",
                    description=str(event.get("description", "")),
                    milestone_type="ci_handoff",
                    status=_milestone_status_from_event(event),
                    owner="CI Owner",
                    event=event,
                    target_environment=str(event.get("related_environment", "unknown")),
                )
            )
    return out


def build_release_milestones(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    milestones: List[Dict[str, Any]] = []
    for event in events:
        event_type = str(event.get("event_type", "unknown"))
        if event_type == "readiness_report":
            milestones.append(milestone_from_readiness_event(event))
        elif event_type == "gate_decision":
            milestones.append(milestone_from_gate_event(event))
        elif event_type == "scenario_comparison":
            milestones.append(milestone_from_scenario_event(event))
    milestones.extend(milestones_from_promotion_events(events))
    return milestones


def summarize_release_milestones(milestones: List[Dict[str, Any]]) -> Dict[str, Any]:
    escalation_hints: List[str] = []
    blocked_count = 0
    status_counts: Dict[str, int] = {}
    for milestone in milestones:
        status = str(milestone.get("status", "unknown"))
        status_counts[status] = status_counts.get(status, 0) + 1
        if status == "blocked":
            blocked_count += 1
        blockers = milestone.get("blockers", [])
        warnings = milestone.get("warnings", [])
        if isinstance(blockers, list) and blockers:
            escalation_hints.append(f"{milestone.get('title', 'milestone')} has blockers")
        if str(milestone.get("target_environment")) == "production" and status == "blocked":
            escalation_hints.append("Production promotion is blocked")
        if str(milestone.get("milestone_type")) == "rollback" and isinstance(warnings, list) and warnings:
            escalation_hints.append("Rollback requirements have missing artifacts")
        if str(milestone.get("milestone_type")) == "ci_handoff" and status in {"review_required", "blocked"}:
            escalation_hints.append("CI handoff requirements need review")
        if str(milestone.get("milestone_type")) == "readiness":
            desc = str(milestone.get("description", ""))
            if "score=" in desc:
                try:
                    score = float(desc.split("score=")[-1].strip())
                    if score < 70:
                        escalation_hints.append("Readiness score below threshold")
                except Exception:
                    pass
        if str(milestone.get("milestone_type")) == "scenario" and status == "review_required":
            escalation_hints.append("Scenario strategies disagree and need review")
    return {
        "milestone_count": len(milestones),
        "blocked_count": blocked_count,
        "status_counts": status_counts,
        "escalation_hints": _dedupe(escalation_hints),
    }


def _make_milestone(
    *,
    title: str,
    description: str,
    milestone_type: str,
    status: str,
    owner: str,
    event: Dict[str, Any],
    target_environment: str | None = None,
) -> Dict[str, Any]:
    blockers = event.get("blockers", []) if isinstance(event.get("blockers"), list) else []
    warnings = event.get("warnings", []) if isinstance(event.get("warnings"), list) else []
    escalation_hints: List[str] = []
    if blockers:
        escalation_hints.append("Resolve blockers before promotion")
    if target_environment == "production" and blockers:
        escalation_hints.append("Escalate production blocker to Release Owner")
    return ReleaseMilestone(
        milestone_id=new_id("release_milestone"),
        title=title,
        description=description,
        milestone_type=milestone_type,  # type: ignore[arg-type]
        status=status,  # type: ignore[arg-type]
        target_environment=target_environment,
        owner_placeholder=owner,
        related_event_ids=[str(event.get("event_id", ""))],
        blockers=[str(b) for b in blockers if isinstance(b, str)],
        warnings=[str(w) for w in warnings if isinstance(w, str)],
        escalation_hints=escalation_hints,
        metadata={"advisory_only": True},
    ).to_dict()


def _milestone_status_from_event(event: Dict[str, Any]) -> str:
    status = str(event.get("status", "unknown"))
    mapping = {
        "ready": "ready",
        "review_required": "review_required",
        "blocked": "blocked",
        "completed": "completed",
        "observed": "in_progress",
        "unknown": "unknown",
    }
    return mapping.get(status, "unknown")


def _dedupe(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out

