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

from remediation_planner.contracts import (  # noqa: E402
    validate_remediation_batch_dict,
    validate_remediation_item_dict,
    validate_remediation_plan_report_dict,
)


class TestRemediationPlannerContracts(unittest.TestCase):
    def test_valid_contracts(self) -> None:
        item = {
            "item_id": "i1",
            "title": "Fix config",
            "description": "desc",
            "category": "config",
            "priority": "P2",
            "status": "open",
            "repository": "REMOTE-AGENTS",
            "source_finding_ids": ["f1"],
            "suggested_action": "Do thing",
            "risk_score": 80,
            "effort_score": 30,
            "confidence_score": 85,
            "advisory_only": True,
            "metadata": {},
        }
        batch = {
            "batch_id": "b1",
            "name": "Batch",
            "priority": "P2",
            "status": "planned",
            "repository": "REMOTE-AGENTS",
            "item_ids": ["i1"],
            "estimated_total_effort": 30,
            "expected_risk_reduction": 80,
            "advisory_only": True,
            "metadata": {},
        }
        report = {
            "report_id": "r1",
            "generated_utc": "2026-01-01T00:00:00Z",
            "source_report_id": "s1",
            "overall_status": "warning",
            "items": [item],
            "batches": [batch],
            "recommended_sequence": ["b1"],
            "summary": {},
            "advisory_only": True,
            "metadata": {},
        }
        validate_remediation_item_dict(item)
        validate_remediation_batch_dict(batch)
        validate_remediation_plan_report_dict(report)


if __name__ == "__main__":
    unittest.main()
