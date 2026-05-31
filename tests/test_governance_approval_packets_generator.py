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

from governance_approval_packets.generator import generate_governance_approval_packet_report  # noqa: E402


class TestGovernanceApprovalPacketsGenerator(unittest.TestCase):
    def test_generates_only_ready_and_needs_review(self) -> None:
        report = generate_governance_approval_packet_report(
            readiness_report={
                "report_id": "rr1",
                "records": [
                    {"record_id": "r1", "dossier_id": "d1", "title": "T1", "approval_status": "ready_for_review", "readiness_score": 90, "risk_level": "medium", "approval_recommendation": "", "required_human_review": False},
                    {"record_id": "r2", "dossier_id": "d2", "title": "T2", "approval_status": "needs_review", "readiness_score": 60, "risk_level": "high", "approval_recommendation": "", "required_human_review": True},
                    {"record_id": "r3", "dossier_id": "d3", "title": "T3", "approval_status": "blocked", "readiness_score": 20, "risk_level": "low", "approval_recommendation": "", "required_human_review": True},
                ],
            },
            dossier_report={
                "report_id": "dr1",
                "dossiers": [
                    {"dossier_id": "d1", "target_artifacts": ["a"], "validation_commands": ["v1"], "rollback_guidance": ["r1"]},
                    {"dossier_id": "d2", "target_artifacts": ["b"], "validation_commands": ["v2"], "rollback_guidance": ["r2"]},
                    {"dossier_id": "d3", "target_artifacts": ["c"], "validation_commands": ["v3"], "rollback_guidance": ["r3"]},
                ],
            },
        )
        self.assertEqual(len(report["packets"]), 2)
        self.assertEqual(report["summary"]["skipped_blocked_or_rejected"], 1)

    def test_human_template_blank_and_non_executing(self) -> None:
        report = generate_governance_approval_packet_report(
            readiness_report={"report_id": "rr1", "records": [{"record_id": "r1", "dossier_id": "d1", "title": "T1", "approval_status": "ready_for_review", "readiness_score": 90, "risk_level": "low", "approval_recommendation": "", "required_human_review": False}]},
            dossier_report={"report_id": "dr1", "dossiers": [{"dossier_id": "d1", "target_artifacts": [], "validation_commands": [], "rollback_guidance": []}]},
        )
        pkt = report["packets"][0]
        hdt = pkt["human_decision_template"]
        self.assertEqual(hdt["required_reviewer"], "")
        self.assertEqual(hdt["decision_notes_placeholder"], "")
        self.assertIn("does NOT grant approval", pkt["review_summary"])


if __name__ == "__main__":
    unittest.main()

