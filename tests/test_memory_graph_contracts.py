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

from memory_graph.contracts import create_edge, create_node, validate_edge_dict, validate_node_dict  # noqa: E402


class TestMemoryGraphContracts(unittest.TestCase):
    def test_valid_node_passes_validation(self) -> None:
        node = create_node(node_id="mission:1", node_type="mission", label="Mission 1", metadata={"x": 1})
        validate_node_dict(node.to_dict())
        self.assertEqual(node.node_type, "mission")

    def test_invalid_node_type_fails(self) -> None:
        node = create_node(node_id="mission:1", node_type="mission", label="Mission 1").to_dict()
        node["node_type"] = "unknown"
        with self.assertRaises(ValueError):
            validate_node_dict(node)

    def test_valid_edge_passes_validation(self) -> None:
        edge = create_edge(from_node_id="mission:1", to_node_id="task:1", edge_type="contains")
        validate_edge_dict(edge.to_dict())
        self.assertEqual(edge.edge_type, "contains")

    def test_invalid_edge_type_fails(self) -> None:
        edge = create_edge(from_node_id="mission:1", to_node_id="task:1", edge_type="contains").to_dict()
        edge["edge_type"] = "teleports_to"
        with self.assertRaises(ValueError):
            validate_edge_dict(edge)


if __name__ == "__main__":
    unittest.main()
