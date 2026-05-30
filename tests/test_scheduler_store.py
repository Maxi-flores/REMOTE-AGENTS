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

from scheduler.contracts import create_task_lease, create_worker_descriptor  # noqa: E402
from scheduler.store import SchedulerStateStore  # noqa: E402


class TestSchedulerStore(unittest.TestCase):
    def test_store_can_register_and_list_workers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SchedulerStateStore(Path(tmp) / ".scheduler" / "state.json")
            worker = create_worker_descriptor(
                worker_id="worker_1",
                worker_type="local_mcp",
                display_name="Local MCP",
                status="idle",
                capabilities=["workspace_file_router"],
                supported_providers=["mcp"],
            )
            store.register_worker(worker)
            workers = store.list_workers()
            self.assertEqual(len(workers), 1)
            self.assertEqual(workers[0]["worker_id"], "worker_1")

    def test_store_can_update_worker_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SchedulerStateStore(Path(tmp) / ".scheduler" / "state.json")
            store.register_worker(
                create_worker_descriptor(worker_id="worker_1", worker_type="local_mcp", display_name="Local")
            )
            updated = store.update_worker_status("worker_1", "busy")
            self.assertEqual(updated["status"], "busy")

    def test_store_can_create_renew_and_release_leases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SchedulerStateStore(Path(tmp) / ".scheduler" / "state.json")
            lease = create_task_lease(
                lease_id="lease_1",
                task_id="task_1",
                worker_id="worker_1",
                expires_utc="2099-01-01T00:00:00Z",
            )
            store.create_lease(lease)
            self.assertEqual(len(store.list_active_leases()), 1)
            renewed = store.renew_lease("lease_1", "2099-01-02T00:00:00Z")
            self.assertEqual(renewed["lease_status"], "renewed")
            released = store.release_lease("lease_1")
            self.assertEqual(released["lease_status"], "released")
            self.assertEqual(store.list_active_leases(), [])

    def test_stale_leases_expire_correctly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SchedulerStateStore(Path(tmp) / ".scheduler" / "state.json")
            store.create_lease(
                create_task_lease(
                    lease_id="lease_old",
                    task_id="task_old",
                    worker_id="worker_1",
                    expires_utc="2020-01-01T00:00:00Z",
                )
            )
            expired = store.expire_stale_leases("2020-01-02T00:00:00Z")
            self.assertEqual(len(expired), 1)
            self.assertEqual(expired[0]["lease_status"], "expired")
            self.assertEqual(store.list_active_leases(), [])

    def test_append_scheduler_event(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = SchedulerStateStore(Path(tmp) / ".scheduler" / "state.json")
            event = store.append_scheduler_event({"event_type": "planned"})
            self.assertEqual(event["event_type"], "planned")
            self.assertIn("created_utc", event)


if __name__ == "__main__":
    unittest.main()
