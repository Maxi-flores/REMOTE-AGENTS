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

from governance_approval_readiness.contracts import (  # noqa: E402
    GovernanceApprovalReadinessRecord,
    GovernanceApprovalReadinessReport,
    validate_governance_approval_readiness_record_dict,
    validate_governance_approval_readiness_report_dict,
)


class TestGovernanceApprovalReadinessContracts(unittest.TestCase):
    def test_valid_record(self) -> None:
        record = GovernanceApprovalReadinessRecord(
            record_id="r1",
            dossier_id="d1",
            title="Title",
            approval_status="ready_for_review",
            readiness_score=90,
            risk_level="low",
            missing_requirements=[],
            approval_recommendation="Proceed",
            required_human_review=False,
            advisory_only=True,
            metadata={},
        ).to_dict()
        validate_governance_approval_readiness_record_dict(record)

    def test_invalid_status(self) -> None:
        record = {
            "record_id": "r1",
            "dossier_id": "d1",
            "title": "Title",
            "approval_status": "bad",
            "readiness_score": 90,
            "risk_level": "low",
            "missing_requirements": [],
            "approval_recommendation": "Proceed",
            "required_human_review": False,
            "advisory_only": True,
            "metadata": {},
        }
        with self.assertRaises(ValueError):
            validate_governance_approval_readiness_record_dict(record)

    def test_valid_report(self) -> None:
        report = GovernanceApprovalReadinessReport(
            report_id="rr1",
            generated_utc="2026-01-01T00:00:00Z",
            source_dossier_report_id="dr1",
            records=[],
            summary={},
            advisory_only=True,
            metadata={},
        ).to_dict()
        validate_governance_approval_readiness_report_dict(report)


if __name__ == "__main__":
    unittest.main()

