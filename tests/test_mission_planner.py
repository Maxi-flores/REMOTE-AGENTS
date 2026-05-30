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

from mission_engine.contracts import create_mission  # noqa: E402
from mission_engine.planner import plan_mission  # noqa: E402


class TestMissionPlanner(unittest.TestCase):
    def test_single_repo_plan_assigns_agents_from_legacy_router(self) -> None:
        mission = create_mission(
            title="Fix Vite proxy",
            instruction="Update Vite proxy config",
            target_repository="ConceptSHOP",
        )
        planned = plan_mission(mission)
        self.assertEqual(planned.status, "planned")
        self.assertEqual(len(planned.tasks), 1)
        self.assertEqual(planned.tasks[0].assigned_primary_agent, "ViteReactPrimaryAgent")
        self.assertEqual(planned.tasks[0].assigned_twin_agent, "ViteReactTwinAgent")

    def test_multi_repo_plan_creates_one_task_per_repository(self) -> None:
        mission = create_mission(
            title="Audit build scripts",
            instruction="Audit build scripts and document missing commands",
            target_repositories=["Powerframe", "PowerStarter"],
            priority=1,
        )
        planned = plan_mission(mission)
        self.assertEqual(len(planned.tasks), 2)
        self.assertEqual([task.target_repository for task in planned.tasks], ["Powerframe", "PowerStarter"])
        self.assertTrue(all(task.assigned_primary_agent == "MonorepoHubPrimaryAgent" for task in planned.tasks))
        self.assertTrue(all(task.assigned_twin_agent == "MonorepoHubTwinAgent" for task in planned.tasks))


if __name__ == "__main__":
    unittest.main()
