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

from mission_engine.contracts import (  # noqa: E402
    MISSION_STATUSES,
    TASK_STATUSES,
    Mission,
    MissionTask,
    create_mission,
    create_task,
    validate_mission_dict,
    validate_task_dict,
)


class TestMissionContracts(unittest.TestCase):
    def test_mission_contract_validation_round_trip(self) -> None:
        mission = create_mission(
            title="Fix Vite proxy",
            instruction="Update Vite proxy config",
            target_repository="ConceptSHOP",
            priority=2,
        )
        payload = mission.to_dict()
        validate_mission_dict(payload)
        restored = Mission.from_dict(payload)
        self.assertEqual(restored.mission_id, mission.mission_id)
        self.assertEqual(restored.target_repository, "ConceptSHOP")
        self.assertIn(restored.status, MISSION_STATUSES)

    def test_task_contract_validation_round_trip(self) -> None:
        task = create_task(
            mission_id="mission_test",
            instruction="Do one thing",
            target_repository="ConceptSHOP",
            assigned_primary_agent="ViteReactPrimaryAgent",
            assigned_twin_agent="ViteReactTwinAgent",
            priority=1,
        )
        payload = task.to_dict()
        validate_task_dict(payload)
        restored = MissionTask.from_dict(payload)
        self.assertEqual(restored.mission_id, "mission_test")
        self.assertEqual(restored.assigned_primary_agent, "ViteReactPrimaryAgent")
        self.assertIn(restored.status, TASK_STATUSES)

    def test_invalid_status_is_rejected(self) -> None:
        mission = create_mission(title="Bad", instruction="Bad")
        payload = mission.to_dict()
        payload["status"] = "wandering"
        with self.assertRaises(ValueError):
            validate_mission_dict(payload)


if __name__ == "__main__":
    unittest.main()
