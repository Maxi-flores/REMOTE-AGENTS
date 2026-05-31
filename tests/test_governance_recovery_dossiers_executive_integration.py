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


class TestGovernanceRecoveryDossiersExecutiveIntegration(unittest.TestCase):
    def test_finding_added_when_dossiers_present(self) -> None:
        analysis = analyze_artifacts(
            governance_recovery_dossier_report={
                "report_id": "d1",
                "dossiers": [{"dossier_id": "x1", "execution_risk": "high"}],
            }
        )
        titles = [f.get("title", "") for f in analysis.get("findings", []) if isinstance(f, dict)]
        self.assertTrue(any("execution dossiers available" in t.lower() for t in titles))


if __name__ == "__main__":
    unittest.main()

