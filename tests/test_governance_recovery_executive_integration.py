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


class TestGovernanceRecoveryExecutiveIntegration(unittest.TestCase):
    def test_executive_summary_signal(self) -> None:
        analyzed = analyze_artifacts(governance_recovery_report={"actions": [{"action_id": "a1"}], "waves": [{"wave_id": "w1"}]})
        titles = [str(f.get("title") or "") for f in analyzed.get("findings", []) if isinstance(f, dict)]
        self.assertTrue(any("recovery plan" in t.lower() for t in titles))


if __name__ == "__main__":
    unittest.main()

