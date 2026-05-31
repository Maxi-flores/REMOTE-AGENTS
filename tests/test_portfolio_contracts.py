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

from portfolio_orchestration.contracts import (  # noqa: E402
    PortfolioReport,
    new_id,
    utc_now,
    validate_portfolio_report_dict,
)


class TestPortfolioContracts(unittest.TestCase):
    def test_validate_report(self) -> None:
        payload = PortfolioReport(
            report_id=new_id("portfolio_report"),
            generated_utc=utc_now(),
            repositories=[
                {
                    "repository_id": "REMOTE-AGENTS",
                    "repository_name": "REMOTE-AGENTS",
                    "repository_path": ".",
                    "repository_type": "agent",
                    "enabled": True,
                    "metadata": {},
                }
            ],
            repository_statuses=[
                {
                    "repository_id": "REMOTE-AGENTS",
                    "health_score": 80,
                    "remediation_count": 0,
                    "queue_count": 0,
                    "dossier_count": 0,
                    "readiness_score": 0,
                    "overall_status": "warning",
                    "metadata": {},
                }
            ],
            findings=[],
            portfolio_health_score=80,
            portfolio_readiness_score=70,
            recommended_execution_order=["REMOTE-AGENTS"],
            advisory_only=True,
            metadata={},
        ).to_dict()
        validate_portfolio_report_dict(payload)


if __name__ == "__main__":
    unittest.main()

