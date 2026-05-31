from __future__ import annotations

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

from governance_recovery_dossiers.generator import generate_governance_recovery_dossier_report  # noqa: E402


class TestGovernanceRecoveryDossiersGenerator(unittest.TestCase):
    def test_action_to_dossier_and_wave_grouping(self) -> None:
        report = generate_governance_recovery_dossier_report(
            recovery_report={
                "report_id": "gr1",
                "actions": [
                    {
                        "action_id": "a1",
                        "title": "Resolve P1 onboarding recommendations",
                        "description": "Close onboarding gaps",
                        "priority": "P1",
                        "target_component": "Onboarding Coverage",
                        "recommended_commands": ["python src/portfolio_onboarding_recommendations/cli.py --export --export-jsonl"],
                        "expected_score_impact": 10,
                    }
                ],
                "waves": [{"wave_id": "wave_1", "actions": ["a1"], "title": "Wave 1"}],
            }
        )
        self.assertEqual(len(report["dossiers"]), 1)
        dossier = report["dossiers"][0]
        self.assertEqual(dossier["source_wave_id"], "wave_1")
        self.assertIn(".control_plane/portfolio_onboarding_recommendations/latest.json", dossier["target_artifacts"])
        self.assertIn("advisory-only", dossier["codex_prompt"].lower())
        self.assertEqual(report["wave_summary"][0]["wave_id"], "wave_1")

    def test_missing_recovery_file_safe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = generate_governance_recovery_dossier_report(base_dir=Path(tmp))
            self.assertEqual(report["source_recovery_report_id"], "missing_governance_recovery_report")
            self.assertEqual(report["dossiers"], [])


if __name__ == "__main__":
    unittest.main()

