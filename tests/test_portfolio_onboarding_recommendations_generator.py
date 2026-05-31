from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from portfolio_onboarding_recommendations.generator import generate_portfolio_onboarding_recommendation_report  # noqa: E402


class TestPortfolioOnboardingRecommendationGenerator(unittest.TestCase):
    def test_recommendations_generated_for_states(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".control_plane" / "portfolio_bootstrap").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "portfolio_bootstrap" / "latest.json").write_text(
                json.dumps(
                    {
                        "report_id": "bootstrap_1",
                        "onboarding_records": [
                            {
                                "repository_id": "A",
                                "repository_name": "A",
                                "repository_path": ".",
                                "discovered": False,
                                "artifact_status": "unknown",
                                "readiness_estimate": 0,
                                "onboarding_state": "registered",
                                "metadata": {},
                            },
                            {
                                "repository_id": "B",
                                "repository_name": "B",
                                "repository_path": ".",
                                "discovered": True,
                                "artifact_status": "none",
                                "readiness_estimate": 40,
                                "onboarding_state": "discovered",
                                "metadata": {},
                            },
                            {
                                "repository_id": "C",
                                "repository_name": "C",
                                "repository_path": ".",
                                "discovered": True,
                                "artifact_status": "complete",
                                "readiness_estimate": 100,
                                "onboarding_state": "onboarded",
                                "metadata": {},
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            report = generate_portfolio_onboarding_recommendation_report(base_dir=root)
            self.assertEqual(report["source_bootstrap_report_id"], "bootstrap_1")
            self.assertEqual(len(report["recommendations"]), 3)
            priorities = {r["repository_id"]: r["priority"] for r in report["recommendations"]}
            self.assertEqual(priorities["A"], "P1")
            self.assertEqual(priorities["B"], "P1")
            self.assertEqual(priorities["C"], "P3")


if __name__ == "__main__":
    unittest.main()

