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

from mission_engine.contracts import create_mission, create_task  # noqa: E402
from mission_engine.store import MissionStore  # noqa: E402


class TestMissionStore(unittest.TestCase):
    def test_create_read_update_append_and_archive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = MissionStore(Path(tmp) / ".missions")
            mission = create_mission(title="Audit", instruction="Audit build scripts", target_repository="Powerframe")
            store.create_mission(mission)

            loaded = store.read_mission(mission.mission_id)
            self.assertEqual(loaded.title, "Audit")

            task = create_task(
                mission_id=mission.mission_id,
                instruction=mission.instruction,
                target_repository="Powerframe",
                assigned_primary_agent="MonorepoHubPrimaryAgent",
                assigned_twin_agent="MonorepoHubTwinAgent",
            )
            updated = store.append_task(mission.mission_id, task)
            self.assertEqual(updated.status, "planned")
            self.assertEqual(len(updated.tasks), 1)

            updated = store.append_telemetry_event(mission.mission_id, {"event": "TEST"})
            self.assertEqual(updated.telemetry_events[-1]["event"], "TEST")

            updated = store.update_mission_status(mission.mission_id, "scheduled")
            self.assertEqual(updated.status, "scheduled")

            archived_path = store.archive_mission(mission.mission_id)
            self.assertTrue(archived_path.exists())
            with self.assertRaises(FileNotFoundError):
                store.read_mission(mission.mission_id)


if __name__ == "__main__":
    unittest.main()
