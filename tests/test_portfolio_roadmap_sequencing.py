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

from portfolio_roadmap.sequencing import dependency_depth, horizon_for_priority, sequence_items, wave_for_horizon_and_depth  # noqa: E402


class TestPortfolioRoadmapSequencing(unittest.TestCase):
    def test_horizon_assignment(self) -> None:
        self.assertEqual(horizon_for_priority("P0"), "near_term")
        self.assertEqual(horizon_for_priority("P2"), "mid_term")
        self.assertEqual(horizon_for_priority("P4"), "long_term")

    def test_dependency_depth(self) -> None:
        graph = {"A": ["B"], "B": ["C"], "C": []}
        self.assertEqual(dependency_depth("A", graph), 2)
        self.assertEqual(wave_for_horizon_and_depth("near_term", 2), "wave_2")

    def test_sequence_items(self) -> None:
        items = [
            {"item_id": "3", "horizon": "long_term", "wave": "wave_3", "priority": "P3", "repository_id": "C"},
            {"item_id": "1", "horizon": "near_term", "wave": "wave_1", "priority": "P1", "repository_id": "A"},
            {"item_id": "2", "horizon": "mid_term", "wave": "wave_2", "priority": "P2", "repository_id": "B"},
        ]
        ordered = sequence_items(items)
        self.assertEqual([i["item_id"] for i in ordered], ["1", "2", "3"])


if __name__ == "__main__":
    unittest.main()

