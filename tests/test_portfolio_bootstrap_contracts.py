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

from portfolio_bootstrap.contracts import (  # noqa: E402
    PortfolioBootstrapReport,
    new_id,
    utc_now,
    validate_portfolio_bootstrap_report_dict,
)


class TestPortfolioBootstrapContracts(unittest.TestCase):
    def test_report_contract(self) -> None:
        payload = PortfolioBootstrapReport(
            report_id=new_id("portfolio_bootstrap_report"),
            generated_utc=utc_now(),
            repositories=[],
            onboarding_records=[
                {
                    "repository_id": "R1",
                    "repository_name": "R1",
                    "repository_path": ".",
                    "discovered": True,
                    "artifact_status": "none",
                    "readiness_estimate": 20,
                    "onboarding_state": "discovered",
                    "metadata": {},
                }
            ],
            readiness_summary={},
            recommendations=[],
            advisory_only=True,
            metadata={},
        ).to_dict()
        validate_portfolio_bootstrap_report_dict(payload)


if __name__ == "__main__":
    unittest.main()

