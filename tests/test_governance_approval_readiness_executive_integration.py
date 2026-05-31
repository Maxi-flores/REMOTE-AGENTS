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


class TestGovernanceApprovalReadinessExecutiveIntegration(unittest.TestCase):
    def test_summary_finding_present(self) -> None:
        analysis = analyze_artifacts(
            governance_approval_readiness_report={
                "summary": {"needs_review": 1, "blocked": 1, "high_risk_count": 0}
            }
        )
        titles = [f.get("title", "") for f in analysis.get("findings", []) if isinstance(f, dict)]
        self.assertTrue(any("approval readiness summary available" in t.lower() for t in titles))


if __name__ == "__main__":
    unittest.main()

