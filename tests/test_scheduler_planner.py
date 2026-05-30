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

from scheduler.contracts import create_worker_descriptor  # noqa: E402
from scheduler.planner import choose_worker_for_task, explain_schedule_decision, plan_task_schedule  # noqa: E402


class TestSchedulerPlanner(unittest.TestCase):
    def test_planner_selects_matching_idle_worker(self) -> None:
        task = {
            "task_id": "task_1",
            "instruction": "Read file",
            "required_tools": ["workspace_file_router"],
            "metadata": {"repository_group": "frontend"},
        }
        workers = [
            create_worker_descriptor(
                worker_id="busy_worker",
                worker_type="local_mcp",
                display_name="Busy",
                status="busy",
                capabilities=["workspace_file_router"],
                supported_providers=["mcp"],
                supported_repository_groups=["frontend"],
            ),
            create_worker_descriptor(
                worker_id="idle_worker",
                worker_type="local_mcp",
                display_name="Idle",
                status="idle",
                capabilities=["workspace_file_router"],
                supported_providers=["mcp"],
                supported_repository_groups=["frontend"],
            ),
        ]
        selected = choose_worker_for_task(task, workers)
        self.assertIsNotNone(selected)
        self.assertEqual(selected["worker_id"], "idle_worker")

    def test_planner_rejects_offline_and_disabled_workers(self) -> None:
        task = {"task_id": "task_1", "required_tools": ["workspace_file_router"]}
        workers = [
            create_worker_descriptor(
                worker_id="offline",
                worker_type="local_mcp",
                display_name="Offline",
                status="offline",
                capabilities=["workspace_file_router"],
                supported_providers=["mcp"],
            ),
            create_worker_descriptor(
                worker_id="disabled",
                worker_type="local_mcp",
                display_name="Disabled",
                status="disabled",
                capabilities=["workspace_file_router"],
                supported_providers=["mcp"],
            ),
        ]
        self.assertIsNone(choose_worker_for_task(task, workers))

    def test_planner_returns_blocked_when_no_worker_matches(self) -> None:
        task = {"task_id": "task_1", "required_tools": ["workspace_file_router"]}
        workers = [
            create_worker_descriptor(
                worker_id="shell_worker",
                worker_type="local_shell",
                display_name="Shell",
                status="idle",
                capabilities=["trace_asset_compilation"],
                supported_providers=["shell"],
            )
        ]
        plan = plan_task_schedule(task, workers)
        self.assertEqual(plan["status"], "blocked")
        self.assertFalse(plan["queue_mutation"])

    def test_explain_schedule_decision_is_metadata_only(self) -> None:
        task = {
            "task_id": "task_1",
            "target_repository": "ConceptSHOP",
            "required_tools": ["workspace_file_router"],
            "metadata": {"repository_group": "frontend"},
        }
        worker = {"worker_id": "worker_1", "status": "idle"}
        explanation = explain_schedule_decision(task, worker, "matching_worker_selected")
        self.assertEqual(explanation["task_id"], "task_1")
        self.assertEqual(explanation["worker_id"], "worker_1")
        self.assertFalse(explanation["queue_mutation"])


if __name__ == "__main__":
    unittest.main()
