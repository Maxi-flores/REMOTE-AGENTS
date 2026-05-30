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


class TestExecutiveBriefingAnalyzer(unittest.TestCase):
    def test_detects_non_ok_orchestration_stage(self) -> None:
        result = analyze_artifacts(
            orchestration_report={
                "stage_results": [
                    {"stage_name": "mission", "status": "ok"},
                    {"stage_name": "release_readiness", "status": "warning"},
                ]
            }
        )
        self.assertGreaterEqual(len(result["findings"]), 1)
        self.assertTrue(any(f.get("category") == "release" for f in result["findings"]))

    def test_detects_lifecycle_gaps(self) -> None:
        result = analyze_artifacts(lifecycle_state={"capability_profiles": {}, "lifecycle_states": {}})
        titles = [f.get("title", "") for f in result["findings"]]
        self.assertTrue(any("capability profiles" in str(t).lower() for t in titles))


if __name__ == "__main__":
    unittest.main()

