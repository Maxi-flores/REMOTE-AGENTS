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

from governance_recovery_dossiers.contracts import (  # noqa: E402
    GovernanceRecoveryDossier,
    GovernanceRecoveryDossierReport,
    validate_governance_recovery_dossier_dict,
    validate_governance_recovery_dossier_report_dict,
)


class TestGovernanceRecoveryDossiersContracts(unittest.TestCase):
    def test_valid_dossier(self) -> None:
        dossier = GovernanceRecoveryDossier(
            dossier_id="d1",
            source_action_id="a1",
            source_wave_id="wave_1",
            title="Dossier",
            objective="Objective",
            target_component="Governance",
            target_artifacts=[".control_plane/portfolio_governance_index/latest.json"],
            recommended_commands=["python src/portfolio_governance_index/cli.py --print"],
            validation_commands=["python src/portfolio_orchestration/cli.py --print"],
            review_checklist=["Check"],
            rollback_guidance=["Restore artifact"],
            codex_prompt="Prompt",
            execution_risk="medium",
            advisory_only=True,
            metadata={},
        ).to_dict()
        validate_governance_recovery_dossier_dict(dossier)

    def test_invalid_risk(self) -> None:
        dossier = {
            "dossier_id": "d1",
            "source_action_id": "a1",
            "source_wave_id": "wave_1",
            "title": "Dossier",
            "objective": "Objective",
            "target_component": "Governance",
            "target_artifacts": [],
            "recommended_commands": [],
            "validation_commands": [],
            "review_checklist": [],
            "rollback_guidance": [],
            "codex_prompt": "Prompt",
            "execution_risk": "invalid",
            "advisory_only": True,
            "metadata": {},
        }
        with self.assertRaises(ValueError):
            validate_governance_recovery_dossier_dict(dossier)

    def test_valid_report(self) -> None:
        report = GovernanceRecoveryDossierReport(
            report_id="r1",
            generated_utc="2026-01-01T00:00:00Z",
            source_recovery_report_id="gr1",
            dossiers=[],
            wave_summary=[],
            advisory_only=True,
            metadata={},
        ).to_dict()
        validate_governance_recovery_dossier_report_dict(report)


if __name__ == "__main__":
    unittest.main()

