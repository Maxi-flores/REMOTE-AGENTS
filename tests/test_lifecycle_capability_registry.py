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

from lifecycle_manager.capability_registry import (  # noqa: E402
    build_capability_profiles,
    load_agents_registry,
    load_repositories_registry,
    load_tools_registry,
)


class TestLifecycleCapabilityRegistry(unittest.TestCase):
    def test_builder_tolerates_missing_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            agents = load_agents_registry(base / "missing_agents.json")
            tools = load_tools_registry(base / "missing_tools.json")
            repos = load_repositories_registry(base / "missing_repos.json")
            profiles = build_capability_profiles(agents, tools, repos)
            self.assertEqual(profiles, [])

    def test_builder_infers_repository_coverage(self) -> None:
        agents = load_agents_registry(REPO_ROOT / "config" / "registries" / "agents.json")
        tools = load_tools_registry(REPO_ROOT / "config" / "registries" / "tools.json")
        repos = load_repositories_registry(REPO_ROOT / "config" / "registries" / "repositories.json")
        profiles = build_capability_profiles(agents, tools, repos)
        self.assertGreater(len(profiles), 0)
        covered = [p for p in profiles if isinstance(p.get("repositories"), list) and p.get("repositories")]
        self.assertGreater(len(covered), 0)


if __name__ == "__main__":
    unittest.main()

