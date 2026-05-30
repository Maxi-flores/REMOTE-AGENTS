from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from sentient_ui.exporter import build_and_export_view_model, export_view_model_jsonl  # noqa: E402


class TestSentientUiExporter(unittest.TestCase):
    def test_exporter_writes_only_under_sentient_ui(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            cp = base / ".control_plane"
            cp.mkdir(parents=True, exist_ok=True)
            (cp / "snapshot.json").write_text(json.dumps({"snapshot_id": "s1", "generated_utc": "t", "schema_version": 1}), encoding="utf-8")
            out = base / ".sentient_ui" / "view_model.json"
            build_and_export_view_model(snapshot_path=cp / "snapshot.json", history_path=cp / "snapshots.jsonl", output_path=out)
            self.assertTrue(out.exists())
            with self.assertRaises(ValueError):
                build_and_export_view_model(snapshot_path=cp / "snapshot.json", output_path=base / "view_model.json")

    def test_jsonl_export_appends_valid_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            cp = base / ".control_plane"
            cp.mkdir(parents=True, exist_ok=True)
            (cp / "snapshot.json").write_text(json.dumps({"snapshot_id": "s1", "generated_utc": "t", "schema_version": 1}), encoding="utf-8")
            out = base / ".sentient_ui" / "view_models.jsonl"
            export_view_model_jsonl(snapshot_path=cp / "snapshot.json", history_path=cp / "snapshots.jsonl", output_path=out)
            export_view_model_jsonl(snapshot_path=cp / "snapshot.json", history_path=cp / "snapshots.jsonl", output_path=out)
            lines = [line for line in out.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(len(lines), 2)
            for line in lines:
                payload = json.loads(line)
                self.assertIn("view_model_id", payload)


if __name__ == "__main__":
    unittest.main()

