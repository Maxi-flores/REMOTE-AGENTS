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

from portfolio_critical_path.contracts import (  # noqa: E402
    PortfolioCriticalPathReport,
    new_id,
    utc_now,
    validate_portfolio_critical_path_report_dict,
)


class TestPortfolioCriticalPathContracts(unittest.TestCase):
    def test_contract(self) -> None:
        payload = PortfolioCriticalPathReport(
            report_id=new_id("pcpi"),
            generated_utc=utc_now(),
            critical_repository_scores=[
                {
                    "repository_id": "A",
                    "repository_name": "A",
                    "consumer_count": 1,
                    "provider_count": 1,
                    "dependency_chain_count": 1,
                    "propagated_risk_count": 1,
                    "readiness_score": 30,
                    "influence_score": 40,
                    "critical_path_score": 70,
                    "advisory_only": True,
                    "metadata": {},
                }
            ],
            recommendations=[
                {
                    "recommendation_id": "r1",
                    "repository_id": "A",
                    "priority": "P1",
                    "title": "t",
                    "rationale": "r",
                    "expected_portfolio_impact": "i",
                    "recommended_action": "a",
                    "dependency_refs": [],
                    "advisory_only": True,
                    "metadata": {},
                }
            ],
            top_critical_repositories=["A"],
            top_dependency_chains=[["A", "B"]],
            portfolio_leverage_summary={},
            advisory_only=True,
            metadata={},
        ).to_dict()
        validate_portfolio_critical_path_report_dict(payload)


if __name__ == "__main__":
    unittest.main()

