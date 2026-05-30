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

from strategic_missions.scoring import derive_priority, score_finding  # noqa: E402


class TestStrategicMissionsScoring(unittest.TestCase):
    def test_scores_finding(self) -> None:
        scores = score_finding({"severity": "high", "category": "release"})
        self.assertGreaterEqual(scores["risk_reduction_score"], 80)
        self.assertGreaterEqual(scores["confidence_score"], 80)

    def test_priority_derivation(self) -> None:
        self.assertEqual(derive_priority(risk_reduction_score=95, effort_score=30, confidence_score=90), "P0")
        self.assertIn(
            derive_priority(risk_reduction_score=50, effort_score=50, confidence_score=70),
            {"P2", "P3", "P4"},
        )


if __name__ == "__main__":
    unittest.main()

