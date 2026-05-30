from __future__ import annotations

from typing import Any, Dict, List, Optional


def build_metric_series(history: List[Dict[str, Any]], section_name: str, metric_name: str) -> List[Dict[str, Any]]:
    series: List[Dict[str, Any]] = []
    for snapshot in history:
        section = snapshot.get(section_name)
        metrics = section.get("metrics") if isinstance(section, dict) else {}
        value = metrics.get(metric_name) if isinstance(metrics, dict) else None
        series.append(
            {
                "snapshot_id": snapshot.get("snapshot_id"),
                "generated_utc": snapshot.get("generated_utc"),
                "value": value,
            }
        )
    return series


def compute_delta(current_value: Any, previous_value: Any) -> Optional[float]:
    if not isinstance(current_value, (int, float)) or isinstance(current_value, bool):
        return None
    if not isinstance(previous_value, (int, float)) or isinstance(previous_value, bool):
        return None
    return float(current_value) - float(previous_value)


def compute_status_trend(history: List[Dict[str, Any]], section_name: str) -> Dict[str, Any]:
    statuses = []
    for snapshot in history:
        section = snapshot.get(section_name)
        if isinstance(section, dict):
            status = section.get("status")
            if isinstance(status, str):
                statuses.append(status)
    if not statuses:
        return {"current": "unknown", "previous": "unknown", "changed": False}
    current = statuses[-1]
    previous = statuses[-2] if len(statuses) > 1 else current
    return {"current": current, "previous": previous, "changed": current != previous}


def summarize_recent_alerts(history: List[Dict[str, Any]], limit: int = 20) -> List[Dict[str, Any]]:
    alerts: List[Dict[str, Any]] = []
    for snapshot in reversed(history):
        generated = snapshot.get("generated_utc")
        for key, section in snapshot.items():
            if not isinstance(section, dict):
                continue
            section_alerts = section.get("alerts")
            if not isinstance(section_alerts, list):
                continue
            for alert in section_alerts:
                if not isinstance(alert, dict):
                    continue
                alerts.append(
                    {
                        "generated_utc": generated,
                        "section": key,
                        "level": alert.get("level", "info"),
                        "message": alert.get("message", ""),
                    }
                )
    return alerts[: max(limit, 0)]

