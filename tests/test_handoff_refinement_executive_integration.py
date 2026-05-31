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

from executive_briefing.analyzer import analyze_artifacts  # noqa: E402


class TestHandoffRefinementExecutiveIntegration(unittest.TestCase):
    def test_refinement_findings_appear(self) -> None:
        result = analyze_artifacts(
            handoff_refinement_report={
                "split_summary": {"split_delta": 3, "high_risk_refined_count": 1},
                "refined_packages": [{"refined_package_id": "r1"}],
            }
        )
        titles = [str(f.get("title", "")).lower() for f in result["findings"]]
        self.assertTrue(any("refined" in t for t in titles))


if __name__ == "__main__":
    unittest.main()
