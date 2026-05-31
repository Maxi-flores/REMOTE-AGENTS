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

from manual_execution_queue.contracts import (  # noqa: E402
    ManualExecutionQueueItem,
    validate_manual_execution_queue_item_dict,
)


class TestManualExecutionQueueContracts(unittest.TestCase):
    def test_valid_item(self) -> None:
        item = ManualExecutionQueueItem(
            queue_item_id="q1",
            packet_id="p1",
            source_dossier_id="d1",
            decision="defer",
            queue_status="deferred",
            title="T1",
            priority="P3",
            operator_next_step="Review later",
            validation_commands=[],
            safety_notes=[],
            advisory_only=True,
            metadata={},
        ).to_dict()
        validate_manual_execution_queue_item_dict(item)

    def test_invalid_status(self) -> None:
        with self.assertRaises(ValueError):
            validate_manual_execution_queue_item_dict(
                {
                    "queue_item_id": "q1",
                    "packet_id": "p1",
                    "source_dossier_id": "d1",
                    "decision": "defer",
                    "queue_status": "bad",
                    "title": "T1",
                    "priority": "P3",
                    "operator_next_step": "Review later",
                    "validation_commands": [],
                    "safety_notes": [],
                    "advisory_only": True,
                    "metadata": {},
                }
            )


if __name__ == "__main__":
    unittest.main()

