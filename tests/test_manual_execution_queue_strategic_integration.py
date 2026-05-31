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


class TestManualExecutionQueueStrategicIntegration(unittest.TestCase):
    def test_queue_candidates(self) -> None:
        report = generate_strategic_mission_report(
            briefing={"overall_status": "healthy", "top_risks": [], "recommended_actions": []},
            manual_execution_queue_report={
                "report_id": "mq1",
                "summary": {"pending_review": 2, "deferred": 1, "needs_changes": 1, "approved_manual": 1},
            },
        )
        titles = [c.get("title", "") for c in report.get("candidates", []) if isinstance(c, dict)]
        self.assertTrue(any("Review pending manual execution handoff queue items" in t for t in titles))
        self.assertTrue(any("needing changes" in t for t in titles))


if __name__ == "__main__":
    unittest.main()

