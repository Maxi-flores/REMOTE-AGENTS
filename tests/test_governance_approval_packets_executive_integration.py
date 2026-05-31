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


class TestGovernanceApprovalPacketsExecutiveIntegration(unittest.TestCase):
    def test_packet_summary_finding(self) -> None:
        analysis = analyze_artifacts(
            governance_approval_packet_report={
                "summary": {"packets_generated": 3, "needs_review_packets": 1}
            }
        )
        titles = [f.get("title", "") for f in analysis.get("findings", []) if isinstance(f, dict)]
        self.assertTrue(any("approval packets available" in t.lower() for t in titles))


if __name__ == "__main__":
    unittest.main()

