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


class TestRemediationPlannerExecutiveIntegration(unittest.TestCase):
    def test_executive_includes_remediation_risk(self) -> None:
        result = analyze_artifacts(
            remediation_plan_report={
                "items": [
                    {"item_id": "i1", "priority": "P1"},
                    {"item_id": "i2", "priority": "P3"},
                ]
            }
        )
        titles = [str(f.get("title", "")).lower() for f in result["findings"]]
        self.assertTrue(any("remediation backlog" in title for title in titles))


if __name__ == "__main__":
    unittest.main()
