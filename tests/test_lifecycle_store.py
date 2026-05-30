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

from lifecycle_manager.lifecycle_manager import create_lifecycle_state  # noqa: E402
from lifecycle_manager.store import LifecycleStore  # noqa: E402
from lifecycle_manager.utils import utc_now  # noqa: E402


class TestLifecycleStore(unittest.TestCase):
    def test_store_profiles_and_agents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = LifecycleStore(Path(tmp) / ".lifecycle" / "agents.json")
            profile = {
                "capability_profile_id": "cp1",
                "agent_class": "A1",
                "display_name": "Agent One",
                "category": "execution",
                "repositories": [],
                "repository_groups": [],
                "capabilities": [],
                "allowed_tools": [],
                "denied_tools": [],
                "risk_tier": "medium",
                "primary_roles": [],
                "secondary_roles": [],
                "health_requirements": {},
                "performance_metrics": {},
                "status": "active",
                "created_utc": utc_now(),
                "updated_utc": utc_now(),
                "metadata": {},
            }
            store.upsert_capability_profile(profile)
            self.assertEqual(len(store.list_capability_profiles()), 1)
            agent = create_lifecycle_state("A1")
            store.register_agent(agent)
            self.assertEqual(len(store.list_agents()), 1)
            store.update_agent_health(agent["agent_id"], "healthy")
            store.update_agent_availability(agent["agent_id"], "busy")
            updated = store.get_agent(agent["agent_id"])
            self.assertEqual(updated["health"], "healthy")
            self.assertEqual(updated["availability"], "busy")


if __name__ == "__main__":
    unittest.main()

