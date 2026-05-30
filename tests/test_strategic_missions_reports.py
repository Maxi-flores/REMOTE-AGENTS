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

from strategic_missions.reports import (  # noqa: E402
    append_strategic_mission_report_jsonl,
    write_strategic_mission_report,
)


class TestStrategicMissionsReports(unittest.TestCase):
    def test_write_report_under_control_plane_strategic_missions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            out = write_strategic_mission_report(
                {"report_id": "r1"},
                path=base / ".control_plane" / "strategic_missions" / "strategic_mission_report.json",
            )
            self.assertTrue(out.exists())
            self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["report_id"], "r1")

    def test_append_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            out = append_strategic_mission_report_jsonl(
                {"report_id": "r2"},
                path=base / ".control_plane" / "strategic_missions" / "strategic_mission_reports.jsonl",
            )
            lines = out.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 1)
            self.assertEqual(json.loads(lines[0])["report_id"], "r2")


if __name__ == "__main__":
    unittest.main()

