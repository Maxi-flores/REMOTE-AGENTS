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

from portfolio_progress.contracts import PortfolioProgressReport, new_id, utc_now, validate_portfolio_progress_report_dict  # noqa: E402


class TestPortfolioProgressContracts(unittest.TestCase):
    def test_contract(self) -> None:
        report = PortfolioProgressReport(
            report_id=new_id("ppr"),
            generated_utc=utc_now(),
            metrics=[
                {
                    "metric_id": "m1",
                    "repository_id": "portfolio",
                    "metric_name": "portfolio_health_score",
                    "current_value": 10,
                    "previous_value": 8,
                    "delta": 2,
                    "trend": "improving",
                    "advisory_only": True,
                    "metadata": {},
                }
            ],
            findings=[
                {
                    "finding_id": "f1",
                    "severity": "low",
                    "repository_id": "portfolio",
                    "title": "t",
                    "description": "d",
                    "trend": "stable",
                    "recommended_action": "a",
                    "advisory_only": True,
                    "metadata": {},
                }
            ],
            portfolio_trends={"overall_trend": "improving"},
            advisory_only=True,
            metadata={},
        ).to_dict()
        validate_portfolio_progress_report_dict(report)


if __name__ == "__main__":
    unittest.main()

