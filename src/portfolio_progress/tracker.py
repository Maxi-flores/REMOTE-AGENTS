from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


POSITIVE_METRICS = {
    "portfolio_health_score",
    "portfolio_readiness_score",
    "onboarding_average_readiness",
    "repository_health_score",
    "repository_readiness_score",
    "repository_onboarding_readiness",
}

NEGATIVE_METRICS = {
    "onboarding_unknown_count",
    "dependency_finding_count",
    "dependency_high_count",
    "critical_path_recommendation_count",
    "roadmap_item_count",
    "roadmap_wave_count",
    "repository_dependency_findings",
    "drift_finding_count",
}


def load_json(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def load_latest_and_previous(directory: str | Path) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    root = Path(directory)
    latest = load_json(root / "latest.json")
    previous = _from_history_jsonl(root / "history.jsonl", latest_report_id=str(latest.get("report_id") or ""))
    return latest, previous


def compute_delta(current_value: float | int | None, previous_value: float | int | None) -> float | None:
    if current_value is None or previous_value is None:
        return None
    return float(current_value) - float(previous_value)


def compute_trend(metric_name: str, current_value: float | int | None, previous_value: float | int | None) -> str:
    if current_value is None or previous_value is None:
        return "unknown"
    delta = float(current_value) - float(previous_value)
    if delta == 0:
        return "stable"
    if metric_name in POSITIVE_METRICS:
        return "improving" if delta > 0 else "declining"
    if metric_name in NEGATIVE_METRICS:
        return "improving" if delta < 0 else "declining"
    return "unknown"


def count_dependency_findings(report: Dict[str, Any], *, severity: Iterable[str] | None = None, repository_id: str | None = None) -> int:
    findings = report.get("findings")
    if not isinstance(findings, list):
        return 0
    allowed = {str(s).lower() for s in (severity or [])}
    count = 0
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        if repository_id and str(finding.get("repository_id") or "") != repository_id:
            continue
        if allowed:
            sev = str(finding.get("severity") or "").lower()
            if sev not in allowed:
                continue
        count += 1
    return count


def onboarding_average_readiness(report: Dict[str, Any]) -> int:
    summary = report.get("readiness_summary")
    if isinstance(summary, dict):
        return int(summary.get("average_readiness_estimate") or 0)
    return 0


def onboarding_unknown_count(report: Dict[str, Any]) -> int:
    records = report.get("onboarding_records")
    if not isinstance(records, list):
        return 0
    return sum(
        1
        for record in records
        if isinstance(record, dict) and str(record.get("onboarding_state") or "").lower() in {"unknown", "not_discovered", "not_registered"}
    )


def critical_path_score_map(report: Dict[str, Any]) -> Dict[str, int]:
    scores = report.get("critical_repository_scores")
    if not isinstance(scores, list):
        return {}
    out: Dict[str, int] = {}
    for score in scores:
        if not isinstance(score, dict):
            continue
        rid = str(score.get("repository_id") or "").strip()
        if rid:
            out[rid] = int(score.get("critical_path_score") or 0)
    return out


def onboarding_readiness_map(report: Dict[str, Any]) -> Dict[str, int]:
    records = report.get("onboarding_records")
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


def repository_status_map(report: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
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


def _from_history_jsonl(path: Path, *, latest_report_id: str) -> Dict[str, Any]:
    if not path.exists():
        return {}
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    parsed: List[Dict[str, Any]] = []
    for line in lines:
        try:
            payload = json.loads(line)
        except Exception:
            continue
        if isinstance(payload, dict):
            parsed.append(payload)
    if not parsed:
        return {}
    if latest_report_id:
        parsed = [item for item in parsed if str(item.get("report_id") or "") != latest_report_id]
    if not parsed:
        return {}
    return parsed[-1]
