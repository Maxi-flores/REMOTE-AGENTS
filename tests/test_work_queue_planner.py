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

from work_queue_manager.planner import generate_work_queue_report  # noqa: E402


class TestWorkQueuePlanner(unittest.TestCase):
    def test_planner(self) -> None:
        refinement = {
            "report_id": "r1",
            "refined_packages": [
                {
                    "refined_package_id": "a",
                    "title": "mission_engine add_test refinement",
                    "subsystem": "mission_engine",
                    "change_type": "add_test",
                    "estimated_scope": "small",
                    "risk_level": "low",
                    "target_files": ["tests/test_mission_engine.py"],
                    "validation_commands": ["python -m unittest tests.test_mission_engine -v"],
                    "source_batch_id": "b1",
                },
                {
                    "refined_package_id": "b",
                    "title": "mission_engine add_cli_test refinement",
                    "subsystem": "mission_engine",
                    "change_type": "add_cli_test",
                    "estimated_scope": "small",
                    "risk_level": "low",
                    "target_files": ["tests/test_mission_engine_cli.py"],
                    "validation_commands": ["python -m unittest tests.test_mission_engine_cli -v"],
                    "source_batch_id": "b1",
                },
            ],
        }
        report = generate_work_queue_report(refinement_report=refinement)
        self.assertGreaterEqual(len(report["queue_items"]), 2)
        self.assertIn("dependency_graph", report)


if __name__ == "__main__":
    unittest.main()
