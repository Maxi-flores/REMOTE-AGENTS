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

from portfolio_orchestration.scoring import execution_order, score_portfolio, score_repository_status  # noqa: E402


class TestPortfolioScoring(unittest.TestCase):
    def test_repository_scoring(self) -> None:
        health, readiness, status = score_repository_status(
            remediation_count=3,
            queue_count=2,
            dossier_count=1,
            readiness_score=75,
            intelligence_finding_count=1,
            high_risk_dossier_count=0,
        )
        self.assertIsInstance(health, int)
        self.assertIsInstance(readiness, int)
        self.assertIn(status, {"healthy", "warning", "degraded", "critical", "unknown"})

    def test_portfolio_score_and_order(self) -> None:
        statuses = [
            {"repository_id": "A", "health_score": 80, "readiness_score": 70, "remediation_count": 3},
            {"repository_id": "B", "health_score": 60, "readiness_score": 90, "remediation_count": 2},
        ]
        health, readiness = score_portfolio(statuses)
        self.assertEqual(health, 70)
        self.assertEqual(readiness, 80)
        order = execution_order(statuses)
        self.assertEqual(order[0], "B")


if __name__ == "__main__":
    unittest.main()

