from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

from governance_decisions.contracts import validate_governance_human_decision_record_dict


def load_decisions(path: str | Path = ".control_plane/governance_decisions/decisions.json") -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {"schema_version": 1, "decisions": []}
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"schema_version": 1, "decisions": []}
    if not isinstance(payload, dict):
        return {"schema_version": 1, "decisions": []}
    decisions = payload.get("decisions")
    if not isinstance(decisions, list):
        payload["decisions"] = []
    if not isinstance(payload.get("schema_version"), int):
        payload["schema_version"] = 1
    return payload


def append_decision(
    decision_record: Dict[str, Any],
    *,
    path: str | Path = ".control_plane/governance_decisions/decisions.json",
) -> Dict[str, Any]:
    validate_governance_human_decision_record_dict(decision_record)
    p = Path(path)
    _require_path(p)
    state = load_decisions(p)
    decisions: List[Dict[str, Any]] = [d for d in state.get("decisions", []) if isinstance(d, dict)]
    decision_id = str(decision_record.get("decision_id") or "")
    replaced = False
    for idx, existing in enumerate(decisions):
        if str(existing.get("decision_id") or "") == decision_id:
            decisions[idx] = decision_record
            replaced = True
            break
    if not replaced:
        decisions.append(decision_record)
    state["decisions"] = decisions
    save_decisions(state, path=p)
    return state


def save_decisions(payload: Dict[str, Any], *, path: str | Path = ".control_plane/governance_decisions/decisions.json") -> Path:
    p = Path(path)
    _require_path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(f".{p.name}.tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(tmp, p)
    return p


def _require_path(path: Path) -> None:
    normalized = str(path).replace("\\", "/")
    if "/.control_plane/governance_decisions/" not in f"/{normalized}":
        raise ValueError("path must be under .control_plane/governance_decisions/")

