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

from governance_approval_packets.contracts import (  # noqa: E402
    GovernanceApprovalPacket,
    GovernanceApprovalPacketReport,
    HumanDecisionTemplate,
    validate_governance_approval_packet_dict,
    validate_governance_approval_packet_report_dict,
)


class TestGovernanceApprovalPacketsContracts(unittest.TestCase):
    def test_valid_packet(self) -> None:
        packet = GovernanceApprovalPacket(
            packet_id="p1",
            source_readiness_record_id="r1",
            source_dossier_id="d1",
            title="Title",
            approval_status="ready_for_review",
            readiness_score=90,
            risk_level="medium",
            review_summary="summary",
            target_artifacts=[],
            validation_commands=[],
            rollback_guidance=[],
            human_decision_template=HumanDecisionTemplate(
                allowed_decisions=["approve_for_manual_execution", "request_changes", "reject", "defer"],
                required_reviewer="",
                decision_notes_placeholder="",
                decision_timestamp_placeholder="",
                safety_acknowledgements=[],
            ).to_dict(),
            advisory_only=True,
            metadata={},
        ).to_dict()
        validate_governance_approval_packet_dict(packet)

    def test_invalid_status(self) -> None:
        packet = {
            "packet_id": "p1",
            "source_readiness_record_id": "r1",
            "source_dossier_id": "d1",
            "title": "Title",
            "approval_status": "bad",
            "readiness_score": 90,
            "risk_level": "medium",
            "review_summary": "summary",
            "target_artifacts": [],
            "validation_commands": [],
            "rollback_guidance": [],
            "human_decision_template": {
                "allowed_decisions": ["approve_for_manual_execution"],
                "required_reviewer": "",
                "decision_notes_placeholder": "",
                "decision_timestamp_placeholder": "",
                "safety_acknowledgements": [],
            },
            "advisory_only": True,
            "metadata": {},
        }
        with self.assertRaises(ValueError):
            validate_governance_approval_packet_dict(packet)

    def test_valid_report(self) -> None:
        report = GovernanceApprovalPacketReport(
            report_id="rp1",
            generated_utc="2026-01-01T00:00:00Z",
            source_readiness_report_id="rr1",
            packets=[],
            summary={},
            advisory_only=True,
            metadata={},
        ).to_dict()
        validate_governance_approval_packet_report_dict(report)


if __name__ == "__main__":
    unittest.main()

