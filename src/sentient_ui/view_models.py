from __future__ import annotations

from typing import Any, Dict, List, Optional

from sentient_ui.contracts import PanelViewModel, ViewModelEnvelope, new_id, utc_now
from sentient_ui.trends import compute_status_trend, summarize_recent_alerts


def build_runtime_panel(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    section = _section(snapshot, "runtime")
    metrics = _metrics(section)
    alerts = _alerts_for_runtime(metrics)
    return _panel(
        "runtime_panel",
        "Runtime",
        section.get("status", "unknown"),
        section.get("summary", "Runtime status."),
        metrics=metrics,
        cards=[{"label": "Queue State", "value": metrics.get("state", "unknown")}],
        alerts=alerts,
    )


def build_mission_panel(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    section = _section(snapshot, "missions")
    metrics = _metrics(section)
    records = section.get("records") if isinstance(section.get("records"), list) else []
    return _panel(
        "mission_panel",
        "Missions",
        section.get("status", "unknown"),
        section.get("summary", "Mission summary."),
        metrics=metrics,
        tables=[{"id": "recent_missions", "rows": list(records)}],
        cards=[{"label": "Total Missions", "value": metrics.get("total_missions", 0)}],
    )


def build_agent_panel(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    section = _section(snapshot, "agents")
    metrics = _metrics(section)
    canonical_agents = metrics.get("canonical_agents", 0)
    return _panel(
        "agent_panel",
        "Agents",
        section.get("status", "unknown"),
        "Agent registry footprint and distribution summary.",
        metrics=metrics,
        cards=[{"label": "Agent Count", "value": canonical_agents}],
        tables=[{"id": "agent_distribution", "rows": [{"key": "canonical_agents", "value": canonical_agents}]}],
    )


def build_repository_panel(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    section = _section(snapshot, "repositories")
    metrics = _metrics(section)
    alerts: List[Dict[str, Any]] = []
    if _as_int(metrics.get("health_snapshots")) == 0:
        alerts.append({"level": "warning", "message": "No governance health snapshots recorded."})
    return _panel(
        "repository_panel",
        "Repositories",
        section.get("status", "unknown"),
        section.get("summary", "Repository governance summary."),
        metrics=metrics,
        cards=[
            {"label": "Repositories", "value": metrics.get("canonical_repositories", 0)},
            {"label": "Governance Profiles", "value": metrics.get("governance_profiles", 0)},
            {"label": "Health Snapshots", "value": metrics.get("health_snapshots", 0)},
        ],
        alerts=alerts,
    )


def build_tool_panel(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    section = _section(snapshot, "tools")
    metrics = _metrics(section)
    provider_counts = metrics.get("provider_counts", {})
    risk_counts = metrics.get("risk_counts", {})
    cards = [
        {"label": "Routed Tools", "value": metrics.get("routed_tools", 0)},
        {"label": "Canonical Tools", "value": metrics.get("canonical_tools", 0)},
    ]
    tables = [
        {"id": "providers", "rows": _dict_items(provider_counts)},
        {"id": "risks", "rows": _dict_items(risk_counts)},
    ]
    return _panel(
        "tool_panel",
        "Tools",
        section.get("status", "unknown"),
        section.get("summary", "Tool routing and risk summary."),
        metrics=metrics,
        cards=cards,
        tables=tables,
    )


def build_scheduler_panel(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    section = _section(snapshot, "scheduler")
    metrics = _metrics(section)
    backpressure_state = _metrics(_section(snapshot, "queue")).get("state", "unknown")
    return _panel(
        "scheduler_panel",
        "Scheduler",
        section.get("status", "unknown"),
        "Worker/lease summary with queue backpressure indicator.",
        metrics={**metrics, "queue_backpressure_state": backpressure_state},
        cards=[
            {"label": "Workers", "value": metrics.get("worker_count", 0)},
            {"label": "Active Leases", "value": metrics.get("active_leases", 0)},
            {"label": "Backpressure", "value": backpressure_state},
        ],
    )


def build_memory_panel(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    section = _section(snapshot, "memory_graph")
    metrics = _metrics(section)
    nodes = [{"id": key, "value": value} for key, value in (metrics.get("node_type_counts") or {}).items()]
    edges = [{"id": key, "value": value} for key, value in (metrics.get("edge_type_counts") or {}).items()]
    return _panel(
        "memory_panel",
        "Memory Graph",
        section.get("status", "unknown"),
        section.get("summary", "Semantic memory graph footprint."),
        metrics=metrics,
        graph_nodes=nodes,
        graph_edges=edges,
    )


def build_approval_panel(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    section = _section(snapshot, "approvals")
    metrics = _metrics(section)
    status_counts = metrics.get("approval_status_counts", {})
    pending = _as_int((status_counts or {}).get("requested"))
    alerts = []
    if pending > 0:
        alerts.append({"level": "warning", "message": f"{pending} approval record(s) still requested."})
    return _panel(
        "approval_panel",
        "Approvals",
        section.get("status", "unknown"),
        section.get("summary", "Approval status summary."),
        metrics=metrics,
        tables=[
            {"id": "approval_status", "rows": _dict_items(status_counts)},
            {"id": "approval_action", "rows": _dict_items(metrics.get("approval_action_counts", {}))},
        ],
        alerts=alerts,
    )


def build_consensus_panel(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    section = _section(snapshot, "consensus")
    metrics = _metrics(section)
    decisions = metrics.get("consensus_decision_counts", {})
    rejected = _as_int((decisions or {}).get("rejected"))
    alerts = []
    if rejected > 0:
        alerts.append({"level": "warning", "message": f"{rejected} consensus rejection(s) recorded."})
    return _panel(
        "consensus_panel",
        "Consensus",
        section.get("status", "unknown"),
        section.get("summary", "Consensus decision summary."),
        metrics=metrics,
        tables=[
            {"id": "consensus_type", "rows": _dict_items(metrics.get("consensus_type_counts", {}))},
            {"id": "consensus_decision", "rows": _dict_items(decisions)},
        ],
        alerts=alerts,
    )


def build_observability_panel(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    section = _section(snapshot, "observability")
    metrics = _metrics(section)
    alerts = []
    if _as_int(metrics.get("error_count")) > 0:
        alerts.append({"level": "warning", "message": f"{metrics.get('error_count')} error log entries recorded."})
    return _panel(
        "observability_panel",
        "Observability",
        section.get("status", "unknown"),
        section.get("summary", "Observability summary."),
        metrics=metrics,
        cards=[
            {"label": "Error Count", "value": metrics.get("error_count", 0)},
            {"label": "Consensus Metrics Keys", "value": metrics.get("consensus_metrics_keys", 0)},
        ],
        alerts=alerts,
    )


def build_sentient_view_model(snapshot: Dict[str, Any], history: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    history = history or []
    runtime_panel = build_runtime_panel(snapshot)
    mission_panel = build_mission_panel(snapshot)
    agent_panel = build_agent_panel(snapshot)
    repository_panel = build_repository_panel(snapshot)
    tool_panel = build_tool_panel(snapshot)
    scheduler_panel = build_scheduler_panel(snapshot)
    memory_panel = build_memory_panel(snapshot)
    approval_panel = build_approval_panel(snapshot)
    consensus_panel = build_consensus_panel(snapshot)
    observability_panel = build_observability_panel(snapshot)

    alerts: List[Dict[str, Any]] = []
    for panel in (
        runtime_panel,
        mission_panel,
        agent_panel,
        repository_panel,
        tool_panel,
        scheduler_panel,
        memory_panel,
        approval_panel,
        consensus_panel,
        observability_panel,
    ):
        alerts.extend(panel.get("alerts", []))
    alerts.extend(summarize_recent_alerts(history, limit=20))
    status_trend = compute_status_trend(history, "runtime")

    envelope = ViewModelEnvelope(
        view_model_id=new_id("sentient_view_model"),
        generated_utc=utc_now(),
        source_snapshot_id=str(snapshot.get("snapshot_id") or "unknown_snapshot"),
        schema_version=1,
        runtime_panel=runtime_panel,
        mission_panel=mission_panel,
        agent_panel=agent_panel,
        repository_panel=repository_panel,
        tool_panel=tool_panel,
        scheduler_panel=scheduler_panel,
        memory_panel=memory_panel,
        approval_panel=approval_panel,
        consensus_panel=consensus_panel,
        observability_panel=observability_panel,
        alerts=alerts,
        metadata={
            "history_points": len(history),
            "runtime_status_trend": status_trend,
            "read_only_sources": True,
        },
    )
    return envelope.to_dict()


def _section(snapshot: Dict[str, Any], name: str) -> Dict[str, Any]:
    section = snapshot.get(name)
    return dict(section) if isinstance(section, dict) else {}


def _metrics(section: Dict[str, Any]) -> Dict[str, Any]:
    metrics = section.get("metrics")
    return dict(metrics) if isinstance(metrics, dict) else {}


def _panel(
    panel_id: str,
    title: str,
    status: Any,
    summary: str,
    *,
    metrics: Optional[Dict[str, Any]] = None,
    cards: Optional[List[Dict[str, Any]]] = None,
    tables: Optional[List[Dict[str, Any]]] = None,
    timelines: Optional[List[Dict[str, Any]]] = None,
    graph_nodes: Optional[List[Dict[str, Any]]] = None,
    graph_edges: Optional[List[Dict[str, Any]]] = None,
    alerts: Optional[List[Dict[str, Any]]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return PanelViewModel(
        panel_id=panel_id,
        title=title,
        status=_safe_status(status),
        summary=summary,
        metrics=dict(metrics or {}),
        cards=list(cards or []),
        tables=list(tables or []),
        timelines=list(timelines or []),
        graph_nodes=list(graph_nodes or []),
        graph_edges=list(graph_edges or []),
        alerts=list(alerts or []),
        metadata=dict(metadata or {}),
    ).to_dict()


def _safe_status(value: Any) -> str:
    if isinstance(value, str) and value in {"healthy", "warning", "degraded", "failing", "unknown"}:
        return value
    return "unknown"


def _dict_items(payload: Any) -> List[Dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    return [{"key": str(key), "value": value} for key, value in payload.items()]


def _as_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except Exception:
        return 0


def _alerts_for_runtime(metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
    alerts: List[Dict[str, Any]] = []
    if metrics.get("queue_occupied"):
        alerts.append({"level": "warning", "message": "Legacy queue slot is currently occupied."})
    if metrics.get("lock_present"):
        alerts.append({"level": "warning", "message": "Processing lock is present."})
    return alerts

