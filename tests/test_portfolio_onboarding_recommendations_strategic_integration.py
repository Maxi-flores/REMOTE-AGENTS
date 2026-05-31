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

from strategic_missions.generator import generate_strategic_mission_report  # noqa: E402


class TestPortfolioOnboardingRecommendationStrategicIntegration(unittest.TestCase):
    def test_strategic_candidates_include_onboarding_recommendations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".control_plane" / "portfolio_onboarding_recommendations").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "portfolio_onboarding_recommendations" / "latest.json").write_text(
                json.dumps(
                    {
                        "recommendations": [
                            {
                                "recommendation_id": "r1",
                                "repository_id": "Sentient-OS",
                                "repository_name": "Sentient OS",
                                "priority": "P1",
                                "title": "Sentient OS not discovered",
                                "recommended_actions": ["Verify configured repository path."],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (root / ".control_plane" / "executive").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "executive" / "executive_briefing.json").write_text(
                json.dumps({"overall_status": "healthy", "top_risks": [], "recommended_actions": []}),
                encoding="utf-8",
            )
            report = generate_strategic_mission_report(base_dir=root)
            titles = [str(c.get("title", "")) for c in report["candidates"] if isinstance(c, dict)]
            self.assertTrue(any("Portfolio onboarding recommendation" in t for t in titles))


if __name__ == "__main__":
    unittest.main()

