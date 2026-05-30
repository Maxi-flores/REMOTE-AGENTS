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

from mission_engine.contracts import (  # noqa: E402
    ApprovalRecord,
    approve_record,
    create_approval_request,
    reject_record,
    request_changes_record,
    validate_approval_record_dict,
)


class TestApprovalContracts(unittest.TestCase):
    def test_valid_approval_record_passes_validation(self) -> None:
        record = create_approval_request(
            mission_id="mission_1",
            task_id="task_1",
            requested_by="system",
            risk_tier="standard",
            metadata={"scope": "write"},
        )
        validate_approval_record_dict(record.to_dict())
        restored = ApprovalRecord.from_dict(record.to_dict())
        self.assertEqual(restored.status, "requested")
        self.assertEqual(restored.action, "approve")

    def test_invalid_approval_action_fails_validation(self) -> None:
        record = create_approval_request(mission_id="mission_1", requested_by="system", risk_tier="standard").to_dict()
        record["action"] = "maybe"
        with self.assertRaises(ValueError):
            validate_approval_record_dict(record)

    def test_invalid_approval_status_fails_validation(self) -> None:
        record = create_approval_request(mission_id="mission_1", requested_by="system", risk_tier="standard").to_dict()
        record["status"] = "half_approved"
        with self.assertRaises(ValueError):
            validate_approval_record_dict(record)

    def test_transition_helpers_update_statuses(self) -> None:
        record = create_approval_request(mission_id="mission_1", requested_by="system", risk_tier="high")
        self.assertEqual(approve_record(record, reviewed_by="max").status, "approved")
        self.assertEqual(reject_record(record, reviewed_by="max").status, "rejected")
        self.assertEqual(request_changes_record(record, reviewed_by="max").status, "changes_requested")


if __name__ == "__main__":
    unittest.main()
