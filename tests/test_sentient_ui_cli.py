from __future__ import annotations

import io
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

from sentient_ui.cli import main  # noqa: E402


class TestSentientUiCli(unittest.TestCase):
    def test_cli_print_export_modes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            cp = base / ".control_plane"
            cp.mkdir(parents=True, exist_ok=True)
            snapshot = {
                "snapshot_id": "snap_1",
                "generated_utc": "2026-01-01T00:00:00Z",
                "schema_version": 1,
                "runtime": {"status": "healthy", "summary": "", "metrics": {}},
                "missions": {"status": "healthy", "summary": "", "metrics": {}},
                "agents": {"status": "healthy", "summary": "", "metrics": {}},
                "repositories": {"status": "healthy", "summary": "", "metrics": {}},
                "tools": {"status": "healthy", "summary": "", "metrics": {}},
                "scheduler": {"status": "healthy", "summary": "", "metrics": {}},
                "memory_graph": {"status": "healthy", "summary": "", "metrics": {}},
                "approvals": {"status": "healthy", "summary": "", "metrics": {}},
                "consensus": {"status": "healthy", "summary": "", "metrics": {}},
                "queue": {"status": "healthy", "summary": "", "metrics": {}},
                "observability": {"status": "healthy", "summary": "", "metrics": {}},
                "metadata": {},
            }
            (cp / "snapshot.json").write_text(json.dumps(snapshot), encoding="utf-8")
            output = io.StringIO()
            code = main(["--print", "--base-dir", tmp], stdout=output)
            self.assertEqual(code, 0)
            payload = json.loads(output.getvalue())
            self.assertIn("view_model_id", payload)

            code = main(["--export", "--base-dir", tmp], stdout=io.StringIO())
            self.assertEqual(code, 0)
            self.assertTrue((base / ".sentient_ui" / "view_model.json").exists())

            code = main(["--export-jsonl", "--base-dir", tmp], stdout=io.StringIO())
            self.assertEqual(code, 0)
            self.assertTrue((base / ".sentient_ui" / "view_models.jsonl").exists())

    def test_source_control_plane_files_not_modified(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            cp = base / ".control_plane"
            cp.mkdir(parents=True, exist_ok=True)
            snapshot_file = cp / "snapshot.json"
            snapshot_file.write_text(json.dumps({"snapshot_id": "snap_1", "generated_utc": "t", "schema_version": 1}), encoding="utf-8")
            before = snapshot_file.read_text(encoding="utf-8")
            code = main(["--print", "--base-dir", tmp], stdout=io.StringIO())
            self.assertEqual(code, 0)
            after = snapshot_file.read_text(encoding="utf-8")
            self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()

