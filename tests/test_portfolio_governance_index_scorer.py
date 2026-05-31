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

from portfolio_governance_index.scorer import governance_status, status_for_score, weighted_governance_score  # noqa: E402


class TestPortfolioGovernanceIndexScorer(unittest.TestCase):
    def test_weighted_score_and_status(self) -> None:
        score = weighted_governance_score(
            [
                {"score": 80, "weight": 50},
                {"score": 60, "weight": 50},
            ]
        )
        self.assertEqual(score, 70)
        self.assertEqual(status_for_score(88), "healthy")
        self.assertEqual(governance_status(70, 0), "warning")
        self.assertEqual(governance_status(70, 6), "unknown")


if __name__ == "__main__":
    unittest.main()

