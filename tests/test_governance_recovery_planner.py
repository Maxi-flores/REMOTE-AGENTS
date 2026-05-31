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

from governance_recovery.planner import group_actions_into_waves  # noqa: E402


class TestGovernanceRecoveryPlanner(unittest.TestCase):
    def test_wave_grouping(self) -> None:
        waves = group_actions_into_waves(
            [
                {"action_id": "a1", "priority": "P1", "expected_score_impact": 10},
                {"action_id": "a2", "priority": "P2", "expected_score_impact": 5},
                {"action_id": "a3", "priority": "P3", "expected_score_impact": 3},
            ]
        )
        self.assertEqual(len(waves), 3)
        self.assertEqual(waves[0]["wave_id"], "wave_1")


if __name__ == "__main__":
    unittest.main()

