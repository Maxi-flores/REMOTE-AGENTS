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

from lifecycle_manager.lifecycle_manager import (  # noqa: E402
    build_agent_inventory,
    build_repository_coverage_matrix,
    summarize_repository_agents,
)


class TestLifecycleManager(unittest.TestCase):
    def test_helpers_build_inventory_and_coverage(self) -> None:
        states = [{"agent_id": "a1", "agent_class": "C1", "status": "active", "health": "healthy"}]
        profiles = [
            {
                "agent_class": "C1",
                "repositories": ["Repo1"],
                "primary_roles": ["Repo1"],
                "secondary_roles": ["Repo1"],
                "status": "active",
            }
        ]
        inv = build_agent_inventory(states, profiles)
        self.assertEqual(inv["agent_count"], 1)
        matrix = build_repository_coverage_matrix(profiles)
        self.assertIn("Repo1", matrix)
        summary = summarize_repository_agents("Repo1", states, profiles)
        self.assertIn("C1", summary["covering_agent_classes"])


if __name__ == "__main__":
    unittest.main()

