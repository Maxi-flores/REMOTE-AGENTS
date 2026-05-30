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

from memory_graph.mission_ingest import (  # noqa: E402
    approval_node_id,
    consensus_node_id,
    ingest_approval,
    ingest_consensus,
    ingest_mission_snapshot,
    mission_node_id,
    repository_node_id,
    task_node_id,
)
from memory_graph.store import MemoryGraphStore  # noqa: E402
from mission_engine.contracts import (  # noqa: E402
    approve_record,
    create_approval_request,
    create_consensus_record,
    create_mission,
    create_task,
)


class TestMemoryGraphMissionIngest(unittest.TestCase):
    def test_mission_ingestion_creates_expected_nodes_and_edges(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = MemoryGraphStore(Path(tmp) / ".memory" / "graph.json")
            mission = create_mission(
                mission_id="mission_test",
                title="Fix Vite proxy",
                instruction="Update Vite proxy config",
                target_repository="ConceptSHOP",
            )
            task = create_task(
                mission_id=mission.mission_id,
                task_id="task_test",
                instruction=mission.instruction,
                target_repository="ConceptSHOP",
                assigned_primary_agent="ViteReactPrimaryAgent",
                assigned_twin_agent="ViteReactTwinAgent",
                required_tools=["workspace_file_router"],
            )
            mission.tasks.append(task)
            ingest_mission_snapshot(mission, store=store)

            self.assertIsNotNone(store.get_node(mission_node_id("mission_test")))
            self.assertIsNotNone(store.get_node(task_node_id("task_test")))
            self.assertIsNotNone(store.get_node(repository_node_id("ConceptSHOP")))
            self.assertIsNotNone(store.get_node("agent:ViteReactPrimaryAgent"))
            self.assertIsNotNone(store.get_node("agent:ViteReactTwinAgent"))

            edge_types = {edge["edge_type"] for edge in store.load_graph()["edges"].values()}
            self.assertIn("contains", edge_types)
            self.assertIn("targets_repository", edge_types)
            self.assertIn("assigned_to", edge_types)
            self.assertIn("reviewed_by", edge_types)
            self.assertIn("uses_tool", edge_types)

    def test_approval_and_consensus_ingestion_create_mission_relationships(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = MemoryGraphStore(Path(tmp) / ".memory" / "graph.json")
            mission = create_mission(mission_id="mission_test", title="Review", instruction="Review")
            ingest_mission_snapshot(mission, store=store)
            approval = approve_record(
                create_approval_request(
                    approval_id="approval_test",
                    mission_id=mission.mission_id,
                    requested_by="mission-engine",
                    risk_tier="standard",
                ),
                reviewed_by="max",
            )
            consensus = create_consensus_record(
                consensus_id="consensus_test",
                mission_id=mission.mission_id,
                consensus_type="human",
                decision="approved",
                actor="max",
            )
            ingest_approval(mission.mission_id, approval, store=store)
            ingest_consensus(mission.mission_id, consensus, store=store)

            self.assertIsNotNone(store.get_node(approval_node_id("approval_test")))
            self.assertIsNotNone(store.get_node(consensus_node_id("consensus_test")))
            contains = [
                edge
                for edge in store.list_edges_for_node(mission_node_id(mission.mission_id))
                if edge["edge_type"] == "contains"
            ]
            self.assertGreaterEqual(len(contains), 2)

    def test_ingestion_does_not_touch_legacy_semantic_memory_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = MemoryGraphStore(root / ".memory" / "graph.json")
            mission = create_mission(mission_id="mission_test", title="No legacy touch", instruction="No legacy touch")
            ingest_mission_snapshot(mission, store=store)
            self.assertFalse((root / ".logs" / "semantic_memory.json").exists())


if __name__ == "__main__":
    unittest.main()
