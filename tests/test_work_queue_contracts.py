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

from work_queue_manager.contracts import validate_work_queue_item_dict, validate_work_queue_report_dict  # noqa: E402


class TestWorkQueueContracts(unittest.TestCase):
    def test_validation(self) -> None:
        item = {
            "queue_item_id": "q1",
            "source_refined_package_id": "r1",
            "title": "t",
            "subsystem": "mission_engine",
            "priority": "P1",
            "readiness_score": 95,
            "effort_score": 20,
            "risk_score": 30,
            "blocker_count": 0,
            "dependency_refs": [],
            "recommended_position": 1,
            "execution_readiness": "ready",
            "advisory_only": True,
            "metadata": {},
        }
        report = {
            "report_id": "wr1",
            "generated_utc": "2026-01-01T00:00:00Z",
            "queue_items": [item],
            "dependency_graph": {},
            "blockers": [],
            "recommended_execution_order": ["r1"],
            "advisory_only": True,
            "metadata": {},
        }
        validate_work_queue_item_dict(item)
        validate_work_queue_report_dict(report)


if __name__ == "__main__":
    unittest.main()
