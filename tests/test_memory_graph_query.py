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

from memory_graph.mission_ingest import ingest_mission_snapshot, mission_node_id  # noqa: E402
from memory_graph.query import (  # noqa: E402
    find_agent_tasks,
    find_mission_subgraph,
    find_neighbors,
    find_node,
    find_nodes_by_type,
    find_repository_missions,
)
from memory_graph.store import MemoryGraphStore  # noqa: E402
from mission_engine.contracts import create_mission, create_task  # noqa: E402


class TestMemoryGraphQuery(unittest.TestCase):
    def test_query_helpers_return_expected_subgraph(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = MemoryGraphStore(Path(tmp) / ".memory" / "graph.json")
            mission = create_mission(
                mission_id="mission_test",
                title="Audit",
                instruction="Audit build scripts",
                target_repository="Powerframe",
            )
            mission.tasks.append(
                create_task(
                    mission_id=mission.mission_id,
                    task_id="task_test",
                    instruction=mission.instruction,
                    target_repository="Powerframe",
                    assigned_primary_agent="MonorepoHubPrimaryAgent",
                    assigned_twin_agent="MonorepoHubTwinAgent",
                )
            )
            ingest_mission_snapshot(mission, store=store)

            self.assertIsNotNone(find_node(mission_node_id("mission_test"), store=store))
            self.assertEqual(len(find_nodes_by_type("mission", store=store)), 1)
            self.assertTrue(find_neighbors(mission_node_id("mission_test"), store=store))
            self.assertEqual(len(find_repository_missions("Powerframe", store=store)), 1)
            self.assertEqual(len(find_agent_tasks("MonorepoHubPrimaryAgent", store=store)), 1)
            subgraph = find_mission_subgraph("mission_test", store=store)
            self.assertIn(mission_node_id("mission_test"), subgraph["nodes"])
            self.assertIn("task:task_test", subgraph["nodes"])
            self.assertGreaterEqual(len(subgraph["edges"]), 4)


if __name__ == "__main__":
    unittest.main()
