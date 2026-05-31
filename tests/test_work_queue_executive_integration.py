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


class TestWorkQueueExecutiveIntegration(unittest.TestCase):
    def test_queue_findings(self) -> None:
        result = analyze_artifacts(
            work_queue_report={
                "queue_items": [
                    {"execution_readiness": "ready"},
                    {"execution_readiness": "blocked"},
                    {"execution_readiness": "deferred"},
                ]
            }
        )
        titles = [str(f.get("title", "")).lower() for f in result["findings"]]
        self.assertTrue(any("work queue" in t for t in titles))


if __name__ == "__main__":
    unittest.main()
