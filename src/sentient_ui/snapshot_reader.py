from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def read_latest_snapshot(path: str | Path = ".control_plane/snapshot.json") -> Dict[str, Any]:
    snapshot_path = Path(path)
    if not snapshot_path.exists():
        return {}
    try:
        with snapshot_path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def read_snapshot_history(path: str | Path = ".control_plane/snapshots.jsonl", limit: int = 50) -> List[Dict[str, Any]]:
    history_path = Path(path)
    if not history_path.exists():
        return []
    records: List[Dict[str, Any]] = []
    try:
        with history_path.open("r", encoding="utf-8") as f:
            for line in f:
                raw = line.strip()
                if not raw:
                    continue
                try:
                    payload = json.loads(raw)
                except Exception:
                    continue
                if isinstance(payload, dict):
                    records.append(payload)
    except Exception:
        return []
    if limit <= 0:
        return records
    return records[-limit:]


def safe_snapshot_summary(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(snapshot, dict):
        return {"available": False, "snapshot_id": None, "generated_utc": None, "section_count": 0}
    sections = [
        "runtime",
        "missions",
        "agents",
        "repositories",
        "tools",
        "scheduler",
        "memory_graph",
        "approvals",
        "consensus",
        "queue",
        "observability",
    ]
    count = sum(1 for section in sections if isinstance(snapshot.get(section), dict))
    return {
        "available": True,
        "snapshot_id": snapshot.get("snapshot_id"),
        "generated_utc": snapshot.get("generated_utc"),
        "schema_version": snapshot.get("schema_version"),
        "section_count": count,
    }

