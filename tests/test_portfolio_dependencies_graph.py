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

from portfolio_dependencies.graph import build_dependency_chains, build_dependency_graph  # noqa: E402


class TestPortfolioDependenciesGraph(unittest.TestCase):
    def test_chain(self) -> None:
        graph = build_dependency_graph(
            [
                {"repository_id": "TRT", "depends_on": ["Sentient-OS"]},
                {"repository_id": "Sentient-OS", "depends_on": ["REMOTE-AGENTS"]},
                {"repository_id": "REMOTE-AGENTS", "depends_on": []},
            ]
        )
        chains = build_dependency_chains(graph)
        self.assertTrue(any(chain == ["TRT", "Sentient-OS", "REMOTE-AGENTS"] for chain in chains))


if __name__ == "__main__":
    unittest.main()

