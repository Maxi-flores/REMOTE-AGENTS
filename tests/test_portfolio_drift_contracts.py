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

from portfolio_drift.contracts import PortfolioDriftReport, new_id, utc_now, validate_portfolio_drift_report_dict  # noqa: E402


class TestPortfolioDriftContracts(unittest.TestCase):
    def test_contract(self) -> None:
        payload = PortfolioDriftReport(
            report_id=new_id("drift"),
            generated_utc=utc_now(),
            findings=[
                {
                    "finding_id": "f1",
                    "severity": "medium",
                    "drift_type": "stale_artifact",
                    "source_artifact": "a",
                    "target_artifact": "b",
                    "repository_id": "portfolio",
                    "title": "t",
                    "description": "d",
                    "recommended_action": "r",
                    "advisory_only": True,
                    "metadata": {},
                }
            ],
            summary={},
            advisory_only=True,
            metadata={},
        ).to_dict()
        validate_portfolio_drift_report_dict(payload)


if __name__ == "__main__":
    unittest.main()

