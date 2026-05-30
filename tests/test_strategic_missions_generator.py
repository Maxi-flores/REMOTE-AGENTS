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

from strategic_missions.generator import generate_strategic_mission_report  # noqa: E402


class TestStrategicMissionsGenerator(unittest.TestCase):
    def test_generates_from_briefing_risks(self) -> None:
        briefing = {
            "overall_status": "degraded",
            "top_risks": [
                {
                    "finding_id": "f1",
                    "severity": "high",
                    "category": "lifecycle",
                    "title": "No capability profiles present",
                    "description": "desc",
                    "recommended_action": "Create capability profiles",
                }
            ],
            "recommended_actions": ["Create capability profiles"],
        }
        report = generate_strategic_mission_report(briefing=briefing)
        self.assertGreaterEqual(len(report["candidates"]), 1)
        self.assertIn(report["candidates"][0]["category"], {"lifecycle", "system"})

    def test_healthy_state_generates_maintenance(self) -> None:
        briefing = {"overall_status": "healthy", "top_risks": [], "recommended_actions": []}
        report = generate_strategic_mission_report(briefing=briefing)
        self.assertGreaterEqual(len(report["candidates"]), 1)
        self.assertTrue(all(c["advisory_only"] for c in report["candidates"]))

    def test_reads_latest_briefing_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / ".control_plane" / "executive").mkdir(parents=True, exist_ok=True)
            briefing_path = base / ".control_plane" / "executive" / "executive_briefing.json"
            briefing_path.write_text(
                json.dumps({"overall_status": "healthy", "top_risks": [], "recommended_actions": []}),
                encoding="utf-8",
            )
            report = generate_strategic_mission_report(base_dir=base)
            self.assertIn("report_id", report)


if __name__ == "__main__":
    unittest.main()

