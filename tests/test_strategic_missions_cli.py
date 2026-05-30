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

from strategic_missions.cli import main  # noqa: E402


class TestStrategicMissionsCli(unittest.TestCase):
    def test_print_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / ".control_plane" / "executive").mkdir(parents=True, exist_ok=True)
            (base / ".control_plane" / "executive" / "executive_briefing.json").write_text(
                json.dumps({"overall_status": "healthy", "top_risks": [], "recommended_actions": []}),
                encoding="utf-8",
            )
            out = io.StringIO()
            code = main(["--print", "--base-dir", tmp], stdout=out)
            self.assertEqual(code, 0)
            self.assertIn("Strategic Mission Recommendations", out.getvalue())

    def test_export_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / ".control_plane" / "executive").mkdir(parents=True, exist_ok=True)
            (base / ".control_plane" / "executive" / "executive_briefing.json").write_text(
                json.dumps({"overall_status": "healthy", "top_risks": [], "recommended_actions": []}),
                encoding="utf-8",
            )
            code = main(["--export", "--base-dir", tmp], stdout=io.StringIO())
            self.assertEqual(code, 0)
            self.assertTrue((base / ".control_plane" / "strategic_missions" / "strategic_mission_report.json").exists())

    def test_export_jsonl_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / ".control_plane" / "executive").mkdir(parents=True, exist_ok=True)
            (base / ".control_plane" / "executive" / "executive_briefing.json").write_text(
                json.dumps({"overall_status": "healthy", "top_risks": [], "recommended_actions": []}),
                encoding="utf-8",
            )
            code = main(["--export-jsonl", "--base-dir", tmp], stdout=io.StringIO())
            self.assertEqual(code, 0)
            self.assertTrue((base / ".control_plane" / "strategic_missions" / "strategic_mission_reports.jsonl").exists())


if __name__ == "__main__":
    unittest.main()

