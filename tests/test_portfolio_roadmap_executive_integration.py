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

from executive_briefing.analyzer import analyze_artifacts  # noqa: E402


class TestPortfolioRoadmapExecutiveIntegration(unittest.TestCase):
    def test_executive_finding_for_roadmap(self) -> None:
        report = {
            "roadmap_items": [{"item_id": "i1", "horizon": "near_term"}],
            "waves": [{"wave_id": "wave_1"}],
        }
        analyzed = analyze_artifacts(portfolio_roadmap_report=report)
        findings = analyzed.get("findings", [])
        titles = [str(item.get("title") or "") for item in findings if isinstance(item, dict)]
        self.assertTrue(any("roadmap" in title.lower() for title in titles))


if __name__ == "__main__":
    unittest.main()

