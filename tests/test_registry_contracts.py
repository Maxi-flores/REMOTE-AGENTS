from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from routers.repo_governance_router import resolve_repo_governance_route  # noqa: E402


REGISTRY_DIR = REPO_ROOT / "config" / "registries"


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        obj = json.load(f)
    if not isinstance(obj, dict):
        raise AssertionError(f"{path} must contain a JSON object")
    return obj


class TestRegistryContracts(unittest.TestCase):
    def test_canonical_registry_json_files_parse(self) -> None:
        for name in (
            "repositories.json",
            "agents.json",
            "tools.json",
            "models.json",
            "policies.json",
        ):
            with self.subTest(name=name):
                data = _load_json(REGISTRY_DIR / name)
                self.assertEqual(data.get("schema_version"), 1)

    def test_repository_agent_references_exist_unless_pending_without_assignment(self) -> None:
        repositories = _load_json(REGISTRY_DIR / "repositories.json").get("repositories")
        agents = _load_json(REGISTRY_DIR / "agents.json").get("agents")
        self.assertIsInstance(repositories, list)
        self.assertIsInstance(agents, list)

        agent_ids = {
            agent.get("agent_class_id")
            for agent in agents
            if isinstance(agent, dict) and isinstance(agent.get("agent_class_id"), str)
        }
        self.assertIn("RuntimeDiagnosticAgent", agent_ids)
        self.assertIn("RuntimeDiagnosticTwinAgent", agent_ids)

        for repo in repositories:
            self.assertIsInstance(repo, dict)
            name = repo.get("name")
            status = str(repo.get("status") or "")
            primary = repo.get("primary_agent_class")
            twin = repo.get("twin_agent_class")
            if status.startswith("Pending") and not primary and not twin:
                continue
            with self.subTest(repository=name, agent="primary"):
                self.assertIn(primary, agent_ids)
            with self.subTest(repository=name, agent="twin"):
                self.assertIn(twin, agent_ids)

    def test_legacy_agent_registry_still_routes_through_existing_router(self) -> None:
        known = resolve_repo_governance_route({"target_repository": "ConceptSHOP"})
        self.assertFalse(known.used_default_profile)
        self.assertEqual(known.resolved_repository, "ConceptSHOP")
        self.assertEqual(known.primary_agent_class, "ViteReactPrimaryAgent")
        self.assertEqual(known.twin_agent_class, "ViteReactTwinAgent")

        unknown = resolve_repo_governance_route({"target_repository": "Not-A-Registered-Repo"})
        self.assertTrue(unknown.used_default_profile)
        self.assertEqual(unknown.primary_agent_class, "RuntimeDiagnosticAgent")
        self.assertEqual(unknown.twin_agent_class, "RuntimeDiagnosticTwinAgent")

    def test_platform_mcp_tools_and_canonical_tools_match(self) -> None:
        platform_tools = _load_json(REPO_ROOT / "config" / "platform_mcp_tools.json").get("tools")
        canonical_tools = _load_json(REGISTRY_DIR / "tools.json").get("tools")
        self.assertIsInstance(platform_tools, list)
        self.assertIsInstance(canonical_tools, list)

        platform_names = {
            tool.get("name")
            for tool in platform_tools
            if isinstance(tool, dict) and isinstance(tool.get("name"), str)
        }
        canonical_names = {
            tool.get("name")
            for tool in canonical_tools
            if isinstance(tool, dict) and isinstance(tool.get("name"), str)
        }
        self.assertEqual(platform_names, canonical_names)


if __name__ == "__main__":
    unittest.main()
