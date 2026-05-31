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

from portfolio_progress.tracker import compute_delta, compute_trend  # noqa: E402


class TestPortfolioProgressTracker(unittest.TestCase):
    def test_delta(self) -> None:
        self.assertEqual(compute_delta(10, 8), 2.0)

    def test_positive_trend(self) -> None:
        self.assertEqual(compute_trend("portfolio_health_score", 9, 7), "improving")
        self.assertEqual(compute_trend("portfolio_health_score", 7, 9), "declining")

    def test_negative_trend(self) -> None:
        self.assertEqual(compute_trend("dependency_high_count", 3, 5), "improving")
        self.assertEqual(compute_trend("dependency_high_count", 6, 5), "declining")

    def test_unknown(self) -> None:
        self.assertEqual(compute_trend("portfolio_health_score", 5, None), "unknown")


if __name__ == "__main__":
    unittest.main()

