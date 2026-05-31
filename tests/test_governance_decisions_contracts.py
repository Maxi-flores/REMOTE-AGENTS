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

from governance_decisions.contracts import (  # noqa: E402
    GovernanceHumanDecisionRecord,
    GovernanceDecisionSummaryReport,
    validate_governance_human_decision_record_dict,
)


class TestGovernanceDecisionsContracts(unittest.TestCase):
    def test_valid_decision(self) -> None:
        record = GovernanceHumanDecisionRecord(
            decision_id="d1",
            packet_id="p1",
            source_dossier_id="s1",
            decision="defer",
            reviewer="Max",
            decision_notes="Defer for now",
            decided_utc="2026-01-01T00:00:00Z",
            safety_acknowledgements=[],
            advisory_only=True,
            metadata={},
        ).to_dict()
        validate_governance_human_decision_record_dict(record)

    def test_approve_requires_acks(self) -> None:
        record = {
            "decision_id": "d1",
            "packet_id": "p1",
            "source_dossier_id": "s1",
            "decision": "approve_for_manual_execution",
            "reviewer": "Max",
            "decision_notes": "ok",
            "decided_utc": "2026-01-01T00:00:00Z",
            "safety_acknowledgements": [],
            "advisory_only": True,
            "metadata": {},
        }
        with self.assertRaises(ValueError):
            validate_governance_human_decision_record_dict(record)

    def test_valid_summary_report(self) -> None:
        report = GovernanceDecisionSummaryReport(
            report_id="r1",
            generated_utc="2026-01-01T00:00:00Z",
            source_packet_report_id="p1",
            decisions=[],
            pending_packet_ids=[],
            approved_packet_ids=[],
            request_changes_packet_ids=[],
            rejected_packet_ids=[],
            deferred_packet_ids=[],
            summary={},
            advisory_only=True,
            metadata={},
        ).to_dict()
        self.assertEqual(report["report_id"], "r1")


if __name__ == "__main__":
    unittest.main()

