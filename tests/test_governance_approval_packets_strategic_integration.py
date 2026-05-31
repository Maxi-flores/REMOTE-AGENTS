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


class TestGovernanceApprovalPacketsStrategicIntegration(unittest.TestCase):
    def test_candidate_from_packet(self) -> None:
        report = generate_strategic_mission_report(
            briefing={"overall_status": "healthy", "top_risks": [], "recommended_actions": []},
            governance_approval_packet_report={
                "packets": [
                    {"packet_id": "p1", "title": "Dossier A", "approval_status": "needs_review", "review_summary": "review me"}
                ]
            },
        )
        titles = [c.get("title", "") for c in report.get("candidates", []) if isinstance(c, dict)]
        self.assertTrue(any("Review governance approval packet" in t for t in titles))


if __name__ == "__main__":
    unittest.main()

