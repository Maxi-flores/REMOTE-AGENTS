from __future__ import annotations

from typing import Any, Dict, List

from release_center.timeline_contracts import ReleaseTimelineEvent, new_id, utc_now


def event_from_readiness_report(report: Dict[str, Any]) -> Dict[str, Any]:
    status = str(report.get("readiness_status", "unknown"))
    score = report.get("readiness_score", 0)
    blockers = _list_of_str(report.get("blockers"))
    warnings = _list_of_str(report.get("warnings"))
    severity = "critical" if blockers else ("warning" if warnings else "info")
    return ReleaseTimelineEvent(
        event_id=new_id("release_event"),
        event_type="readiness_report",
        title="Release Readiness Report",
        description=f"Readiness status={status}, score={score}",
        occurred_utc=utc_now(),
        source_artifact=".release_reports/release_readiness.json",
        source_id=str(report.get("report_id")) if isinstance(report.get("report_id"), str) else None,
        severity=severity,  # type: ignore[arg-type]
        status=_normalize_event_status(status),
        blockers=blockers,
        warnings=warnings,
        metadata={"readiness_score": score},
    ).to_dict()


def events_from_gate_trace(trace: Dict[str, Any]) -> List[Dict[str, Any]]:
    decision = trace.get("decision", {}) if isinstance(trace.get("decision"), dict) else {}
    gate_decision = str(decision.get("decision", "unknown"))
    blockers = _list_of_str(decision.get("blockers"))
    warnings = _list_of_str(decision.get("warnings"))
    severity = "critical" if gate_decision == "blocked" else ("warning" if warnings else "info")
    event = ReleaseTimelineEvent(
        event_id=new_id("release_event"),
        event_type="gate_decision",
        title="Gate Decision",
        description=f"Advisory gate decision={gate_decision}",
        occurred_utc=utc_now(),
        source_artifact=".release_reports/gate_trace.json",
        source_id=str(decision.get("decision_id")) if isinstance(decision.get("decision_id"), str) else None,
        severity=severity,  # type: ignore[arg-type]
        status=_status_from_decision(gate_decision),
        related_policy=str(decision.get("policy_id")) if isinstance(decision.get("policy_id"), str) else None,
        blockers=blockers,
        warnings=warnings,
        metadata={"advisory_only": True},
    ).to_dict()
    return [event]


def events_from_scenario_comparison(comparison_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    comparison = (
        comparison_payload.get("comparison")
        if isinstance(comparison_payload.get("comparison"), dict)
        else comparison_payload
    )
    if not isinstance(comparison, dict):
        return []
    aggregate_decision = str(comparison.get("aggregate_decision", "unknown"))
    blockers = _list_of_str(comparison.get("blockers"))
    warnings = _list_of_str(comparison.get("warnings"))
    severity = "critical" if aggregate_decision == "blocked" else ("warning" if warnings else "info")
    event = ReleaseTimelineEvent(
        event_id=new_id("release_event"),
        event_type="scenario_comparison",
        title="Scenario Comparison",
        description=f"Scenario aggregate decision={aggregate_decision}",
        occurred_utc=utc_now(),
        source_artifact=".release_reports/scenario_comparison.json",
        source_id=str(comparison.get("comparison_id")) if isinstance(comparison.get("comparison_id"), str) else None,
        severity=severity,  # type: ignore[arg-type]
        status=_normalize_event_status(str(comparison.get("aggregate_status", "unknown"))),
        related_scenario_pack=str(comparison.get("scenario_pack_id")) if isinstance(comparison.get("scenario_pack_id"), str) else None,
        blockers=blockers,
        warnings=warnings,
        metadata={"comparison_strategy": comparison.get("comparison_strategy")},
    ).to_dict()
    return [event]


def events_from_promotion_report(promotion_report: Dict[str, Any]) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    recommendations = promotion_report.get("recommendations", [])
    if not isinstance(recommendations, list):
        return events
    for rec in recommendations:
        if not isinstance(rec, dict):
            continue
        recommendation = str(rec.get("recommendation", "unknown"))
        env = str(rec.get("target_environment", "unknown"))
        blockers = _list_of_str(rec.get("blockers"))
        warnings = _list_of_str(rec.get("warnings"))
        severity = "critical" if recommendation == "blocked" else ("warning" if warnings else "info")
        events.append(
            ReleaseTimelineEvent(
                event_id=new_id("release_event"),
                event_type="promotion_recommendation",
                title=f"{env.title()} Promotion Recommendation",
                description=f"Recommendation={recommendation}",
                occurred_utc=utc_now(),
                source_artifact=".release_reports/promotion_recommendations.json",
                source_id=str(rec.get("recommendation_id")) if isinstance(rec.get("recommendation_id"), str) else None,
                severity=severity,  # type: ignore[arg-type]
                status=_status_from_decision(recommendation),
                related_environment=env,
                related_profile=str(rec.get("profile_id")) if isinstance(rec.get("profile_id"), str) else None,
                blockers=blockers,
                warnings=warnings,
                metadata={"confidence": rec.get("confidence")},
            ).to_dict()
        )
        rollback = rec.get("rollback_precheck", {})
        if isinstance(rollback, dict):
            events.append(
                ReleaseTimelineEvent(
                    event_id=new_id("release_event"),
                    event_type="rollback_precheck",
                    title=f"{env.title()} Rollback Precheck",
                    description=f"Rollback status={rollback.get('rollback_plan_status', 'unknown')}",
                    occurred_utc=utc_now(),
                    source_artifact=".release_reports/promotion_recommendations.json",
                    severity="warning" if rollback.get("missing_artifacts") else "info",  # type: ignore[arg-type]
                    status="review_required" if rollback.get("missing_artifacts") else "observed",
                    related_environment=env,
                    blockers=[],
                    warnings=_list_of_str(rollback.get("missing_artifacts")),
                    metadata={"rollback_required": rollback.get("rollback_required", False)},
                ).to_dict()
            )
        ci = rec.get("ci_handoff", {})
        if isinstance(ci, dict):
            events.append(
                ReleaseTimelineEvent(
                    event_id=new_id("release_event"),
                    event_type="ci_handoff",
                    title=f"{env.title()} CI Handoff",
                    description=f"Pipeline stage={ci.get('suggested_pipeline_stage', 'unknown')}",
                    occurred_utc=utc_now(),
                    source_artifact=".release_reports/promotion_recommendations.json",
                    severity="warning" if not ci.get("recommended_checks") else "info",  # type: ignore[arg-type]
                    status="review_required" if not ci.get("recommended_checks") else "observed",
                    related_environment=env,
                    blockers=[],
                    warnings=[],
                    metadata={"advisory_gate_decision": ci.get("advisory_gate_decision")},
                ).to_dict()
            )
    return events


def sort_timeline_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(events, key=lambda e: str(e.get("occurred_utc", "")))


def synthesize_release_timeline(
    readiness_report: Dict[str, Any] | None = None,
    gate_trace: Dict[str, Any] | None = None,
    scenario_comparison: Dict[str, Any] | None = None,
    promotion_report: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    if readiness_report:
        events.append(event_from_readiness_report(readiness_report))
    if gate_trace:
        events.extend(events_from_gate_trace(gate_trace))
    if scenario_comparison:
        events.extend(events_from_scenario_comparison(scenario_comparison))
    if promotion_report:
        events.extend(events_from_promotion_report(promotion_report))
    if not events:
        events.append(
            ReleaseTimelineEvent(
                event_id=new_id("release_event"),
                event_type="advisory_note",
                title="No Release Artifacts Found",
                description="No readiness/gate/scenario/promotion artifacts were available.",
                occurred_utc=utc_now(),
                source_artifact=".release_reports/",
                severity="info",
                status="unknown",
                blockers=[],
                warnings=[],
                metadata={"advisory_only": True},
            ).to_dict()
        )
    return sort_timeline_events(events)


def _normalize_event_status(value: str) -> str:
    value = value if value in {"observed", "ready", "review_required", "blocked", "completed", "unknown"} else "unknown"
    return value


def _status_from_decision(decision: str) -> str:
    if decision == "blocked":
        return "blocked"
    if decision in {"pass_with_warnings", "promote_with_warnings", "mixed"}:
        return "review_required"
    if decision in {"pass", "promote"}:
        return "ready"
    if decision in {"hold"}:
        return "observed"
    return "unknown"


def _list_of_str(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(v) for v in value if isinstance(v, str)]

