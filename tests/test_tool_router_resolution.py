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

from tool_router.router import (  # noqa: E402
    list_tool_routes,
    load_canonical_tool_registry,
    load_legacy_platform_tools,
    resolve_tool_route,
    tool_exists,
)


class TestToolRouterResolution(unittest.TestCase):
    def test_canonical_tools_registry_parses(self) -> None:
        registry = load_canonical_tool_registry()
        self.assertEqual(registry.get("schema_version"), 1)
        self.assertIsInstance(registry.get("tools"), list)

    def test_legacy_platform_tools_config_parses(self) -> None:
        registry = load_legacy_platform_tools()
        self.assertEqual(registry.get("schema_version"), 1)
        self.assertIsInstance(registry.get("tools"), list)

    def test_resolve_known_tool_route(self) -> None:
        route = resolve_tool_route("workspace_file_router")
        self.assertEqual(route.tool_name, "workspace_file_router")
        self.assertEqual(route.implementation_status, "active")
        self.assertEqual(route.risk_tier, "high")
        self.assertTrue(route.approval_required)
        self.assertTrue(route.metadata["legacy_schema_present"])

    def test_unknown_tool_returns_disabled_high_risk_fallback(self) -> None:
        route = resolve_tool_route("not_a_real_tool")
        self.assertEqual(route.tool_name, "not_a_real_tool")
        self.assertEqual(route.implementation_status, "disabled")
        self.assertEqual(route.risk_tier, "high")
        self.assertTrue(route.approval_required)

    def test_list_routes_and_tool_exists(self) -> None:
        routes = list_tool_routes()
        names = {route.tool_name for route in routes}
        self.assertIn("workspace_file_router", names)
        self.assertTrue(tool_exists("workspace_file_router"))
        self.assertFalse(tool_exists("not_a_real_tool"))

    def test_runtime_context_filter_returns_disabled_route(self) -> None:
        route = resolve_tool_route("workspace_file_router", runtime_context="read_only_diagnostic")
        self.assertEqual(route.implementation_status, "disabled")
        self.assertEqual(route.metadata["disabled_reason"], "runtime_context_not_allowed")


if __name__ == "__main__":
    unittest.main()
