from __future__ import annotations

from typing import Any, Dict, List

from sentient_ui.contracts import PanelViewModel


def build_executive_overview_panel(briefing: Dict[str, Any]) -> Dict[str, Any]:
    return PanelViewModel(
        panel_id="executive_overview_panel",
        title="Executive Overview",
        status=_map_status(str(briefing.get("overall_status") or "unknown")),
        summary=str(briefing.get("executive_summary") or ""),
        metrics={
            "risk_count": len(briefing.get("top_risks", [])) if isinstance(briefing.get("top_risks"), list) else 0,
            "blocked_count": len(briefing.get("blocked_items", [])) if isinstance(briefing.get("blocked_items"), list) else 0,
            "action_count": len(briefing.get("recommended_actions", []))
            if isinstance(briefing.get("recommended_actions"), list)
            else 0,
        },
        cards=[
            {"label": "Overall Status", "value": briefing.get("overall_status", "unknown")},
            {"label": "Top Risks", "value": len(briefing.get("top_risks", [])) if isinstance(briefing.get("top_risks"), list) else 0},
            {"label": "Blocked Items", "value": len(briefing.get("blocked_items", [])) if isinstance(briefing.get("blocked_items"), list) else 0},
        ],
        tables=[{"id": "recommended_actions", "rows": _actions_to_rows(briefing.get("recommended_actions"))}],
        timelines=[],
        graph_nodes=[],
        graph_edges=[],
        alerts=[],
        metadata={"advisory_only": True, "source": "executive_briefing"},
    ).to_dict()


def build_executive_risk_panel(briefing: Dict[str, Any]) -> Dict[str, Any]:
    risks = briefing.get("top_risks", []) if isinstance(briefing.get("top_risks"), list) else []
    alerts: List[Dict[str, Any]] = []
    for risk in risks[:10]:
        if isinstance(risk, dict):
            sev = str(risk.get("severity") or "info")
            if sev in {"high", "critical"}:
                alerts.append({"level": "warning", "message": str(risk.get("title") or "High risk detected")})
    return PanelViewModel(
        panel_id="executive_risk_panel",
        title="Executive Risks",
        status="warning" if alerts else "healthy",
        summary="Top executive risks derived from advisory control-plane signals.",
        metrics={"risk_count": len(risks), "high_critical_count": len(alerts)},
        cards=[{"label": "Risk Items", "value": len(risks)}],
        tables=[{"id": "top_risks", "rows": [r for r in risks if isinstance(r, dict)]}],
        timelines=[],
        graph_nodes=[],
        graph_edges=[],
        alerts=alerts,
        metadata={"advisory_only": True, "source": "executive_briefing"},
    ).to_dict()


def _map_status(value: str) -> str:
    if value == "healthy":
        return "healthy"
    if value == "warning":
        return "warning"
    if value in {"degraded", "blocked"}:
        return "degraded"
    return "unknown"


def _actions_to_rows(actions: Any) -> List[Dict[str, Any]]:
    if not isinstance(actions, list):
        return []
    rows: List[Dict[str, Any]] = []
    for idx, action in enumerate(actions):
        if isinstance(action, str) and action.strip():
            rows.append({"index": idx + 1, "action": action.strip()})
    return rows

