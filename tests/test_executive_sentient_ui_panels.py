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

from sentient_ui.contracts import validate_panel_view_model_dict  # noqa: E402
from sentient_ui.executive_panels import build_executive_overview_panel, build_executive_risk_panel  # noqa: E402


class TestExecutiveSentientUiPanels(unittest.TestCase):
    def test_build_overview_panel(self) -> None:
        panel = build_executive_overview_panel(
            {
                "overall_status": "healthy",
                "executive_summary": "all good",
                "top_risks": [],
                "blocked_items": [],
                "recommended_actions": ["Run readiness analysis"],
            }
        )
        validate_panel_view_model_dict(panel)
        self.assertEqual(panel["title"], "Executive Overview")

    def test_build_risk_panel(self) -> None:
        panel = build_executive_risk_panel(
            {
                "top_risks": [
                    {"severity": "high", "title": "Release readiness score below threshold"},
                ]
            }
        )
        validate_panel_view_model_dict(panel)
        self.assertEqual(panel["title"], "Executive Risks")


if __name__ == "__main__":
    unittest.main()

