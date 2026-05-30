from __future__ import annotations

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

from scheduler.queue_compat import (  # noqa: E402
    can_enqueue_with_single_file_queue,
    describe_legacy_queue_contract,
    explain_queue_backpressure,
)


class TestSchedulerQueueCompat(unittest.TestCase):
    def test_queue_contract_is_read_only_metadata(self) -> None:
        contract = describe_legacy_queue_contract()
        self.assertEqual(contract["queue_path"], ".platform_queue/next_task.json")
        self.assertFalse(contract["scheduler_mutates_queue"])

    def test_queue_helper_detects_occupied_queue_without_mutating(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            queue_path = Path(tmp) / ".platform_queue" / "next_task.json"
            queue_path.parent.mkdir(parents=True)
            queue_path.write_text('{"instruction":"existing"}', encoding="utf-8")
            before = queue_path.read_text(encoding="utf-8")
            self.assertFalse(can_enqueue_with_single_file_queue(queue_path))
            after = queue_path.read_text(encoding="utf-8")
            self.assertEqual(before, after)

    def test_queue_backpressure_explains_lock_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            queue_path = Path(tmp) / ".platform_queue" / "next_task.json"
            lock_path = Path(tmp) / ".platform_queue" / "processing.lock"
            lock_path.parent.mkdir(parents=True)
            lock_path.write_text("locked", encoding="utf-8")
            state = explain_queue_backpressure(queue_path, lock_path)
            self.assertTrue(state["lock_present"])
            self.assertFalse(state["queue_occupied"])
            self.assertEqual(state["state"], "processing_lock_present")
            self.assertFalse(state["queue_mutation"])

    def test_real_legacy_queue_file_is_not_modified(self) -> None:
        queue_path = REPO_ROOT / ".platform_queue" / "next_task.json"
        before = queue_path.read_text(encoding="utf-8") if queue_path.exists() else None
        can_enqueue_with_single_file_queue(queue_path)
        after = queue_path.read_text(encoding="utf-8") if queue_path.exists() else None
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
