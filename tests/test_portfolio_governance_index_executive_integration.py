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


class TestPortfolioGovernanceIndexExecutiveIntegration(unittest.TestCase):
    def test_executive_signal(self) -> None:
        analyzed = analyze_artifacts(
            portfolio_governance_index_report={"governance_score": 55, "governance_status": "degraded"}
        )
        titles = [str(f.get("title") or "") for f in analyzed.get("findings", []) if isinstance(f, dict)]
        self.assertTrue(any("governance index" in title.lower() for title in titles))


if __name__ == "__main__":
    unittest.main()

