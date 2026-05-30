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

from control_plane.cli import main  # noqa: E402


class TestControlPlaneCli(unittest.TestCase):
    def test_cli_print_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            buffer = io.StringIO()
            code = main(["--print", "--base-dir", tmp], stdout=buffer)
            self.assertEqual(code, 0)
            payload = json.loads(buffer.getvalue())
            self.assertIn("snapshot_id", payload)

    def test_cli_export_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            code = main(["--export", "--base-dir", tmp], stdout=io.StringIO())
            self.assertEqual(code, 0)
            self.assertTrue((base / ".control_plane" / "snapshot.json").exists())

    def test_cli_export_jsonl_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            code = main(["--export-jsonl", "--base-dir", tmp], stdout=io.StringIO())
            self.assertEqual(code, 0)
            self.assertTrue((base / ".control_plane" / "snapshots.jsonl").exists())

    def test_source_state_files_are_not_modified(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            mission_dir = base / ".missions"
            mission_dir.mkdir(parents=True)
            mission = mission_dir / "m1.json"
            mission.write_text(
                json.dumps(
                    {
                        "mission_id": "m1",
                        "title": "t",
                        "instruction": "i",
                        "target_repository": None,
                        "target_repositories": [],
                        "priority": 0,
                        "status": "draft",
                        "risk_tier": "standard",
                        "created_utc": "2026-01-01T00:00:00Z",
                        "updated_utc": "2026-01-01T00:00:00Z",
                        "tasks": [],
                        "approvals": [],
                        "consensus_records": [],
                        "telemetry_events": [],
                        "artifacts": [],
                        "failure_reason": None,
                    }
                ),
                encoding="utf-8",
            )
            before = mission.read_text(encoding="utf-8")
            code = main(["--print", "--base-dir", tmp], stdout=io.StringIO())
            self.assertEqual(code, 0)
            after = mission.read_text(encoding="utf-8")
            self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()

