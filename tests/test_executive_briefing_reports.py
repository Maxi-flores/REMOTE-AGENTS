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

from executive_briefing.reports import append_executive_briefing_report_jsonl, write_executive_briefing_report  # noqa: E402


class TestExecutiveBriefingReports(unittest.TestCase):
    def test_write_report_under_control_plane_executive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            out = write_executive_briefing_report(
                {"briefing_id": "b1"},
                path=base / ".control_plane" / "executive" / "executive_briefing.json",
            )
            self.assertTrue(out.exists())
            self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["briefing_id"], "b1")

    def test_append_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            out = append_executive_briefing_report_jsonl(
                {"briefing_id": "b2"},
                path=base / ".control_plane" / "executive" / "executive_briefings.jsonl",
            )
            lines = out.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 1)
            self.assertEqual(json.loads(lines[0])["briefing_id"], "b2")


if __name__ == "__main__":
    unittest.main()

