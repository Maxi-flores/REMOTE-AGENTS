from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def read_latest_readiness_report(path: str | Path = ".release_reports/release_readiness.json") -> Dict[str, Any]:
    return _read_json_file(path)


def read_gate_trace(path: str | Path = ".release_reports/gate_trace.json") -> Dict[str, Any]:
    return _read_json_file(path)


def read_scenario_comparison(path: str | Path = ".release_reports/scenario_comparison.json") -> Dict[str, Any]:
    return _read_json_file(path)


def read_promotion_recommendations(path: str | Path = ".release_reports/promotion_recommendations.json") -> Dict[str, Any]:
    return _read_json_file(path)


def read_release_artifact_history(path: str | Path, limit: int = 100) -> List[Dict[str, Any]]:
    file_path = Path(path)
    if not file_path.exists():
        return []
    out: List[Dict[str, Any]] = []
    try:
        with file_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    parsed = json.loads(line)
                except Exception:
                    continue
                if isinstance(parsed, dict):
                    out.append(parsed)
                    if len(out) >= max(1, int(limit)):
                        break
    except Exception:
        return []
    return out


def _read_json_file(path: str | Path) -> Dict[str, Any]:
    file_path = Path(path)
    if not file_path.exists():
        return {}
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}

