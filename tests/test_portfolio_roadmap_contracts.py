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

from portfolio_roadmap.contracts import PortfolioRoadmapReport, new_id, utc_now, validate_portfolio_roadmap_report_dict  # noqa: E402


class TestPortfolioRoadmapContracts(unittest.TestCase):
    def test_contract(self) -> None:
        payload = PortfolioRoadmapReport(
            report_id=new_id("roadmap"),
            generated_utc=utc_now(),
            source_critical_path_report_id="cp1",
            roadmap_items=[
                {
                    "item_id": "i1",
                    "source_recommendation_id": "r1",
                    "repository_id": "Sentient-OS",
                    "title": "t",
                    "objective": "o",
                    "priority": "P1",
                    "horizon": "near_term",
                    "wave": "wave_1",
                    "dependencies": [],
                    "expected_impact": "i",
                    "validation_focus": [],
                    "advisory_only": True,
                    "metadata": {},
                }
            ],
            waves=[
                {
                    "wave_id": "wave_1",
                    "title": "Near-Term Wave 1",
                    "horizon": "near_term",
                    "objective": "o",
                    "items": ["i1"],
                    "readiness_focus": "r",
                    "risk_focus": "r",
                    "advisory_only": True,
                    "metadata": {},
                }
            ],
            milestones=[],
            recommended_sequence=["i1"],
            advisory_only=True,
            metadata={},
        ).to_dict()
        validate_portfolio_roadmap_report_dict(payload)


if __name__ == "__main__":
    unittest.main()

