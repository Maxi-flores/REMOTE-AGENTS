from __future__ import annotations

import json
import sys
import tempfile
import time
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from mission_engine.contracts import create_approval_request, create_consensus_record, create_mission, create_task  # noqa: E402
from mission_engine.queue_adapter import MissionQueueAdapter  # noqa: E402
from mission_engine.store import MissionStore  # noqa: E402


class TestMissionApprovalConsensusStore(unittest.TestCase):
    def test_append_approval_and_consensus_persist_and_update_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = MissionStore(Path(tmp) / ".missions")
            mission = create_mission(title="Approval test", instruction="Check approval records")
            store.create_mission(mission)
            original_updated = store.read_mission(mission.mission_id).updated_utc

            time.sleep(1.05)
            approval = create_approval_request(
                mission_id=mission.mission_id,
                requested_by="mission-engine",
                risk_tier="standard",
                metadata={"intent": "recordkeeping"},
            )
            with_approval = store.append_approval(mission.mission_id, approval)
            self.assertEqual(len(with_approval.approvals), 1)
            self.assertNotEqual(with_approval.updated_utc, original_updated)
            approval_updated = with_approval.updated_utc

            time.sleep(1.05)
            consensus = create_consensus_record(
                mission_id=mission.mission_id,
                consensus_type="human",
                decision="approved",
                actor="max",
                feedback="Approved for recordkeeping.",
            )
            with_consensus = store.append_consensus_record(mission.mission_id, consensus)
            self.assertEqual(len(with_consensus.consensus_records), 1)
            self.assertNotEqual(with_consensus.updated_utc, approval_updated)

            raw_path = Path(tmp) / ".missions" / f"{mission.mission_id}.json"
            raw = json.loads(raw_path.read_text(encoding="utf-8"))
            self.assertEqual(raw["approvals"][0]["approval_id"], approval.approval_id)
            self.assertEqual(raw["consensus_records"][0]["consensus_id"], consensus.consensus_id)

    def test_queue_adapter_behavior_remains_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            queue_file = Path(tmp) / ".platform_queue" / "next_task.json"
            task = create_task(
                mission_id="mission_1",
                task_id="task_1",
                instruction="Do work",
                target_repository="ConceptSHOP",
                assigned_primary_agent="ViteReactPrimaryAgent",
                assigned_twin_agent="ViteReactTwinAgent",
            )
            result = MissionQueueAdapter(queue_file).enqueue_task(task)
            self.assertTrue(result.enqueued)
            payload = json.loads(queue_file.read_text(encoding="utf-8"))
            self.assertEqual(payload["task_id"], "task_1")
            self.assertEqual(payload["source"], "mission-engine")

            blocked = MissionQueueAdapter(queue_file).enqueue_task(task)
            self.assertFalse(blocked.enqueued)
            self.assertTrue(blocked.blocked)


if __name__ == "__main__":
    unittest.main()
