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

from scheduler.contracts import (  # noqa: E402
    create_task_lease,
    create_worker_descriptor,
    validate_task_lease_dict,
    validate_worker_descriptor_dict,
)


class TestSchedulerContracts(unittest.TestCase):
    def test_valid_worker_descriptor_passes_validation(self) -> None:
        worker = create_worker_descriptor(
            worker_id="worker_local_mcp",
            worker_type="local_mcp",
            display_name="Local MCP Worker",
            status="idle",
            capabilities=["workspace_file_router"],
            supported_providers=["mcp"],
            supported_repository_groups=["frontend"],
            max_concurrent_tasks=1,
            hardware_budget={"memory_mb": 1024},
        )
        validate_worker_descriptor_dict(worker.to_dict())

    def test_invalid_worker_type_fails_validation(self) -> None:
        worker = create_worker_descriptor(worker_type="local_mcp", display_name="Local").to_dict()
        worker["worker_type"] = "space_worker"
        with self.assertRaises(ValueError):
            validate_worker_descriptor_dict(worker)

    def test_invalid_worker_status_fails_validation(self) -> None:
        worker = create_worker_descriptor(worker_type="local_mcp", display_name="Local").to_dict()
        worker["status"] = "wandering"
        with self.assertRaises(ValueError):
            validate_worker_descriptor_dict(worker)

    def test_valid_task_lease_passes_validation(self) -> None:
        lease = create_task_lease(
            lease_id="lease_1",
            task_id="task_1",
            mission_id="mission_1",
            worker_id="worker_1",
            priority=2,
            expires_utc="2099-01-01T00:00:00Z",
        )
        validate_task_lease_dict(lease.to_dict())

    def test_invalid_lease_status_fails_validation(self) -> None:
        lease = create_task_lease(
            task_id="task_1",
            worker_id="worker_1",
            expires_utc="2099-01-01T00:00:00Z",
        ).to_dict()
        lease["lease_status"] = "lost"
        with self.assertRaises(ValueError):
            validate_task_lease_dict(lease)


if __name__ == "__main__":
    unittest.main()
