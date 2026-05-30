from __future__ import annotations

import json
import sys
import tempfile
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


class TestMissionQueueAdapter(unittest.TestCase):
    def test_builds_legacy_compatible_payload(self) -> None:
        task = create_task(
            mission_id="mission_1",
            task_id="task_1",
            instruction="Update Vite proxy config",
            target_repository="ConceptSHOP",
            assigned_primary_agent="ViteReactPrimaryAgent",
            assigned_twin_agent="ViteReactTwinAgent",
            priority=2,
        )
        payload = MissionQueueAdapter().build_payload(task)
        self.assertEqual(payload["task_id"], "task_1")
        self.assertEqual(payload["mission_id"], "mission_1")
        self.assertEqual(payload["instruction"], "Update Vite proxy config")
        self.assertEqual(payload["priority"], 2)
        self.assertEqual(payload["target_repository"], "ConceptSHOP")
        self.assertEqual(payload["source"], "mission-engine")
        self.assertIn("enqueued_utc", payload)

    def test_enqueue_does_not_overwrite_existing_queue_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            queue_file = Path(tmp) / ".platform_queue" / "next_task.json"
            queue_file.parent.mkdir(parents=True)
            queue_file.write_text('{"existing": true}\n', encoding="utf-8")
            task = create_task(
                mission_id="mission_1",
                instruction="Do work",
                target_repository="ConceptSHOP",
                assigned_primary_agent="ViteReactPrimaryAgent",
                assigned_twin_agent="ViteReactTwinAgent",
            )
            result = MissionQueueAdapter(queue_file).enqueue_task(task)
            self.assertFalse(result.enqueued)
            self.assertTrue(result.blocked)
            self.assertEqual(json.loads(queue_file.read_text(encoding="utf-8")), {"existing": True})

    def test_enqueue_writes_when_slot_is_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            queue_file = Path(tmp) / ".platform_queue" / "next_task.json"
            task = create_task(
                mission_id="mission_1",
                instruction="Do work",
                target_repository="ConceptSHOP",
                assigned_primary_agent="ViteReactPrimaryAgent",
                assigned_twin_agent="ViteReactTwinAgent",
            )
            result = MissionQueueAdapter(queue_file).enqueue_task(task)
            self.assertTrue(result.enqueued)
            self.assertFalse(result.blocked)
            written = json.loads(queue_file.read_text(encoding="utf-8"))
            self.assertEqual(written["source"], "mission-engine")
            self.assertEqual(written["task_id"], task.task_id)


if __name__ == "__main__":
    unittest.main()
