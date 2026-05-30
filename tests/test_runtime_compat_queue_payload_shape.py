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

from mission_engine.contracts import create_task  # noqa: E402
from mission_engine.queue_adapter import MissionQueueAdapter  # noqa: E402


class TestRuntimeCompatQueuePayloadShape(unittest.TestCase):
    def test_queue_payload_shape_unchanged(self) -> None:
        task = create_task(
            mission_id="m1",
            task_id="t1",
            instruction="Do thing",
            target_repository="RepoA",
            assigned_primary_agent="PrimaryAgent",
            assigned_twin_agent="TwinAgent",
            priority=2,
        )
        payload = MissionQueueAdapter().build_payload(task)
        expected_keys = {
            "task_id",
            "mission_id",
            "instruction",
            "priority",
            "target_repository",
            "source",
            "enqueued_utc",
        }
        self.assertEqual(set(payload.keys()), expected_keys)
        self.assertEqual(payload["task_id"], "t1")
        self.assertEqual(payload["mission_id"], "m1")
        self.assertEqual(payload["instruction"], "Do thing")
        self.assertEqual(payload["priority"], 2)
        self.assertEqual(payload["target_repository"], "RepoA")
        self.assertEqual(payload["source"], "mission-engine")


if __name__ == "__main__":
    unittest.main()

