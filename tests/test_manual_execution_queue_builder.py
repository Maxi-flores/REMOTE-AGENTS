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

from manual_execution_queue.builder import generate_manual_execution_queue_report  # noqa: E402


class TestManualExecutionQueueBuilder(unittest.TestCase):
    def test_states_generation(self) -> None:
        report = generate_manual_execution_queue_report(
            packet_report={
                "report_id": "p1",
                "packets": [
                    {"packet_id": "a", "source_dossier_id": "d1", "title": "A"},
                    {"packet_id": "b", "source_dossier_id": "d2", "title": "B"},
                    {"packet_id": "c", "source_dossier_id": "d3", "title": "C"},
                    {"packet_id": "d", "source_dossier_id": "d4", "title": "D"},
                    {"packet_id": "e", "source_dossier_id": "d5", "title": "E"},
                ],
            },
            decision_report={
                "report_id": "dr1",
                "decisions": [
                    {"packet_id": "a", "decision": "approve_for_manual_execution"},
                    {"packet_id": "b", "decision": "defer"},
                    {"packet_id": "c", "decision": "request_changes"},
                    {"packet_id": "d", "decision": "reject"},
                ],
            },
        )
        statuses = [item["queue_status"] for item in report["queue_items"]]
        self.assertIn("approved_manual", statuses)
        self.assertIn("deferred", statuses)
        self.assertIn("needs_changes", statuses)
        self.assertIn("rejected", statuses)
        self.assertIn("pending_review", statuses)


if __name__ == "__main__":
    unittest.main()

