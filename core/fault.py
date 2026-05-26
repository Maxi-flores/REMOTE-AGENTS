import json
from pathlib import Path


def dump_critical_misalignment(logs_dir: Path, state: dict, exc: Exception) -> Path:
    logs_dir.mkdir(parents=True, exist_ok=True)
    path = logs_dir / "CRITICAL_MISALIGNMENT.json"
    snapshot = {
        "pipeline_state": "DEAD_HALT",
        "error": repr(exc),
        "state": state,
    }
    path.write_text(json.dumps(snapshot, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
