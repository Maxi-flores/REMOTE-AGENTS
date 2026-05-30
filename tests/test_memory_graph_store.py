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

from memory_graph.contracts import create_edge, create_node  # noqa: E402
from memory_graph.store import MemoryGraphStore  # noqa: E402


class TestMemoryGraphStore(unittest.TestCase):
    def test_storage_can_upsert_read_and_list_nodes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = MemoryGraphStore(Path(tmp) / ".memory" / "graph.json")
            node = create_node(node_id="mission:1", node_type="mission", label="Mission 1", metadata={"a": 1})
            store.upsert_node(node)
            store.upsert_node(create_node(node_id="mission:1", node_type="mission", label="Mission 1", metadata={"b": 2}))
            loaded = store.get_node("mission:1")
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded["metadata"], {"a": 1, "b": 2})
            self.assertEqual(len(store.list_nodes_by_type("mission")), 1)

    def test_storage_can_upsert_read_and_list_edges(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = MemoryGraphStore(Path(tmp) / ".memory" / "graph.json")
            edge = create_edge(from_node_id="mission:1", to_node_id="task:1", edge_type="contains")
            store.upsert_edge(edge)
            self.assertEqual(len(store.list_edges_for_node("mission:1")), 1)
            self.assertEqual(len(store.list_edges_by_type("contains")), 1)


if __name__ == "__main__":
    unittest.main()
