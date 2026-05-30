from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

from sentient_ui.snapshot_reader import read_latest_snapshot, read_snapshot_history
from sentient_ui.view_models import build_sentient_view_model


def build_and_export_view_model(
    snapshot_path: str | Path = ".control_plane/snapshot.json",
    history_path: str | Path = ".control_plane/snapshots.jsonl",
    output_path: str | Path = ".sentient_ui/view_model.json",
) -> Dict[str, Any]:
    snapshot = read_latest_snapshot(snapshot_path)
    history = read_snapshot_history(history_path, limit=50)
    view_model = build_sentient_view_model(snapshot, history=history)
    out_path = Path(output_path)
    _require_sentient_ui_path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_name(f".{out_path.name}.tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(view_model, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp_path, out_path)
    return view_model


def export_view_model_jsonl(
    snapshot_path: str | Path = ".control_plane/snapshot.json",
    history_path: str | Path = ".control_plane/snapshots.jsonl",
    output_path: str | Path = ".sentient_ui/view_models.jsonl",
) -> Dict[str, Any]:
    snapshot = read_latest_snapshot(snapshot_path)
    history = read_snapshot_history(history_path, limit=50)
    view_model = build_sentient_view_model(snapshot, history=history)
    out_path = Path(output_path)
    _require_sentient_ui_path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(view_model, sort_keys=True))
        f.write("\n")
    return view_model


def _require_sentient_ui_path(path: Path) -> None:
    normalized = str(path).replace("\\", "/")
    if "/.sentient_ui/" not in f"/{normalized}":
        raise ValueError("output_path must be under .sentient_ui/")

