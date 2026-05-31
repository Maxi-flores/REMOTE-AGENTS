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

from portfolio_critical_path.scoring import (  # noqa: E402
    compute_critical_path_score,
    compute_influence_score,
)


class TestPortfolioCriticalPathScoring(unittest.TestCase):
    def test_scores(self) -> None:
        influence = compute_influence_score(
            consumer_count=3,
            provider_count=2,
            dependency_chain_count=4,
            propagated_risk_count=2,
            readiness_score=40,
        )
        self.assertGreaterEqual(influence, 0)
        cp = compute_critical_path_score(
            influence_score=influence,
            readiness_score=40,
            downstream_consumers=3,
            high_severity_dependency_findings=2,
            onboarding_priority_weight=8,
        )
        self.assertGreaterEqual(cp, 0)
        self.assertLessEqual(cp, 100)


if __name__ == "__main__":
    unittest.main()

