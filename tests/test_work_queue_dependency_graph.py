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

from work_queue_manager.dependency_graph import build_blockers, infer_dependencies, topological_order  # noqa: E402


class TestWorkQueueDependencyGraph(unittest.TestCase):
    def test_dependency_inference_and_order(self) -> None:
        packages = [
            {"refined_package_id": "a", "subsystem": "mission_engine", "change_type": "add_test"},
            {"refined_package_id": "b", "subsystem": "mission_engine", "change_type": "add_cli_test"},
        ]
        deps = infer_dependencies(packages)
        self.assertIn("a", deps["b"])
        order = topological_order(deps)
        self.assertLess(order.index("a"), order.index("b"))
        blockers = build_blockers(deps, ["a", "b"])
        self.assertEqual(blockers, [])


if __name__ == "__main__":
    unittest.main()
