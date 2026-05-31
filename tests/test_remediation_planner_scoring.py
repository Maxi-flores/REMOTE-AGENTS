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

from remediation_planner.scoring import derive_priority, score_finding  # noqa: E402


class TestRemediationPlannerScoring(unittest.TestCase):
    def test_scores_and_priority(self) -> None:
        scores = score_finding({"severity": "high", "category": "runtime"})
        self.assertGreater(scores["risk_score"], 0)
        self.assertIn(
            derive_priority(
                risk_score=scores["risk_score"],
                effort_score=scores["effort_score"],
                confidence_score=scores["confidence_score"],
            ),
            {"P0", "P1", "P2", "P3", "P4"},
        )


if __name__ == "__main__":
    unittest.main()
