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

from portfolio_onboarding_recommendations.contracts import (  # noqa: E402
    PortfolioOnboardingRecommendationReport,
    new_id,
    utc_now,
    validate_portfolio_onboarding_recommendation_report_dict,
)


class TestPortfolioOnboardingRecommendationContracts(unittest.TestCase):
    def test_report_contract(self) -> None:
        payload = PortfolioOnboardingRecommendationReport(
            report_id=new_id("portfolio_onboarding_recommendation_report"),
            generated_utc=utc_now(),
            source_bootstrap_report_id="bootstrap_1",
            recommendations=[
                {
                    "recommendation_id": "r1",
                    "repository_id": "repo",
                    "repository_name": "repo",
                    "repository_path": ".",
                    "onboarding_state": "registered",
                    "artifact_status": "unknown",
                    "priority": "P1",
                    "title": "title",
                    "recommended_actions": ["x"],
                    "validation_commands": ["y"],
                    "risk_level": "high",
                    "advisory_only": True,
                    "metadata": {},
                }
            ],
            summary={},
            advisory_only=True,
            metadata={},
        ).to_dict()
        validate_portfolio_onboarding_recommendation_report_dict(payload)


if __name__ == "__main__":
    unittest.main()

