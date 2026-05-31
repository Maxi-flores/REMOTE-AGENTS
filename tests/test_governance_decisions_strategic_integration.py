from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from strategic_missions.generator import generate_strategic_mission_report  # noqa: E402


class TestGovernanceDecisionsStrategicIntegration(unittest.TestCase):
    def test_decision_candidates(self) -> None:
        report = generate_strategic_mission_report(
            briefing={"overall_status": "healthy", "top_risks": [], "recommended_actions": []},
            governance_decision_report={
                "report_id": "gr1",
                "summary": {"pending": 1, "request_changes": 1, "approved": 1},
            },
        )
        titles = [c.get("title", "") for c in report.get("candidates", []) if isinstance(c, dict)]
        self.assertTrue(any("Review pending governance decision packets" in t for t in titles))
        self.assertTrue(any("request_changes" in t for t in titles))


if __name__ == "__main__":
    unittest.main()

