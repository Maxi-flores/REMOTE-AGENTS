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

from portfolio_governance_index.contracts import PortfolioGovernanceHealthReport, new_id, utc_now, validate_portfolio_governance_health_report_dict  # noqa: E402


class TestPortfolioGovernanceIndexContracts(unittest.TestCase):
    def test_contract(self) -> None:
        payload = PortfolioGovernanceHealthReport(
            report_id=new_id("ghi"),
            generated_utc=utc_now(),
            governance_score=78,
            governance_status="warning",
            components=[
                {
                    "component_id": "c1",
                    "name": "Portfolio Health",
                    "score": 84,
                    "weight": 20,
                    "status": "healthy",
                    "reasons": [],
                    "advisory_only": True,
                    "metadata": {},
                }
            ],
            top_reasons=[],
            top_recommendations=[],
            advisory_only=True,
            metadata={},
        ).to_dict()
        validate_portfolio_governance_health_report_dict(payload)


if __name__ == "__main__":
    unittest.main()

