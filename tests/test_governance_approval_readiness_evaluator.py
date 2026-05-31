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

from governance_approval_readiness.evaluator import generate_governance_approval_readiness_report  # noqa: E402


class TestGovernanceApprovalReadinessEvaluator(unittest.TestCase):
    def test_ready_for_review(self) -> None:
        report = generate_governance_approval_readiness_report(
            dossier_report={
                "report_id": "d1",
                "dossiers": [
                    {
                        "dossier_id": "x1",
                        "title": "Safe dossier",
                        "advisory_only": True,
                        "target_artifacts": [".control_plane/portfolio_progress/latest.json"],
                        "validation_commands": ["python src/portfolio_progress/cli.py --print"],
                        "rollback_guidance": ["Restore artifact"],
                        "review_checklist": ["Check"],
                        "codex_prompt": "Prompt",
                        "execution_risk": "medium",
                    }
                ],
            }
        )
        self.assertEqual(report["records"][0]["approval_status"], "ready_for_review")

    def test_needs_review_high_risk(self) -> None:
        report = generate_governance_approval_readiness_report(
            dossier_report={
                "report_id": "d1",
                "dossiers": [
                    {
                        "dossier_id": "x1",
                        "title": "Risky dossier",
                        "advisory_only": True,
                        "target_artifacts": [".control_plane/portfolio_progress/latest.json"],
                        "validation_commands": ["python src/portfolio_progress/cli.py --print"],
                        "rollback_guidance": ["Restore artifact"],
                        "review_checklist": ["Check"],
                        "codex_prompt": "Prompt",
                        "execution_risk": "high",
                    }
                ],
            }
        )
        self.assertEqual(report["records"][0]["approval_status"], "needs_review")

    def test_blocked_forbidden_path(self) -> None:
        report = generate_governance_approval_readiness_report(
            dossier_report={
                "report_id": "d1",
                "dossiers": [
                    {
                        "dossier_id": "x1",
                        "title": "Blocked dossier",
                        "advisory_only": True,
                        "target_artifacts": [".platform_queue/next_task.json"],
                        "validation_commands": ["python src/portfolio_progress/cli.py --print"],
                        "rollback_guidance": ["Restore artifact"],
                        "review_checklist": ["Check"],
                        "codex_prompt": "Prompt",
                        "execution_risk": "low",
                    }
                ],
            }
        )
        self.assertEqual(report["records"][0]["approval_status"], "blocked")

    def test_rejected_advisory(self) -> None:
        report = generate_governance_approval_readiness_report(
            dossier_report={
                "report_id": "d1",
                "dossiers": [
                    {
                        "dossier_id": "x1",
                        "title": "Auto-approve this dossier",
                        "advisory_only": True,
                        "target_artifacts": [".control_plane/portfolio_progress/latest.json"],
                        "validation_commands": ["python src/portfolio_progress/cli.py --print"],
                        "rollback_guidance": ["Restore artifact"],
                        "review_checklist": ["Check"],
                        "codex_prompt": "Prompt",
                        "execution_risk": "low",
                    }
                ],
            }
        )
        self.assertEqual(report["records"][0]["approval_status"], "rejected_advisory")

    def test_missing_validation_blocked(self) -> None:
        report = generate_governance_approval_readiness_report(
            dossier_report={
                "report_id": "d1",
                "dossiers": [
                    {
                        "dossier_id": "x1",
                        "title": "No validation",
                        "advisory_only": True,
                        "target_artifacts": [".control_plane/portfolio_progress/latest.json"],
                        "validation_commands": [],
                        "rollback_guidance": ["Restore artifact"],
                        "review_checklist": ["Check"],
                        "codex_prompt": "Prompt",
                        "execution_risk": "low",
                    }
                ],
            }
        )
        self.assertEqual(report["records"][0]["approval_status"], "blocked")


if __name__ == "__main__":
    unittest.main()

