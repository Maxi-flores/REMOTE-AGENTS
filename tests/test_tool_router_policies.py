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

from tool_router.contracts import ToolRoute  # noqa: E402
from tool_router.policies import (  # noqa: E402
    explain_tool_policy,
    is_allowed_for_repository_group,
    is_allowed_in_runtime_context,
    is_network_denied_by_default,
    requires_path_traversal_protection,
    requires_write_approval,
)
from tool_router.router import resolve_tool_route  # noqa: E402


class TestToolRouterPolicies(unittest.TestCase):
    def test_network_tools_denied_by_default_unless_explicitly_allowed(self) -> None:
        route = resolve_tool_route("network_data_fetch")
        self.assertTrue(route.network_access)
        self.assertTrue(is_network_denied_by_default(route))

        allowed = ToolRoute.from_dict(
            {
                **route.to_dict(),
                "metadata": {**route.metadata, "network_explicitly_allowed": True},
            }
        )
        self.assertFalse(is_network_denied_by_default(allowed))

    def test_write_tools_require_approval(self) -> None:
        route = resolve_tool_route("workspace_file_router")
        self.assertTrue(route.write_access)
        self.assertTrue(requires_write_approval(route))

    def test_repo_boundary_and_path_safety_checks_work(self) -> None:
        route = resolve_tool_route("trace_asset_compilation")
        self.assertTrue(route.requires_repo_boundary)
        self.assertTrue(requires_path_traversal_protection(route))

    def test_repository_group_policy(self) -> None:
        route = ToolRoute.from_dict(
            {
                **resolve_tool_route("workspace_file_router").to_dict(),
                "allowed_repository_groups": ["frontend"],
                "denied_repository_groups": ["infra"],
            }
        )
        self.assertTrue(is_allowed_for_repository_group(route, "frontend"))
        self.assertFalse(is_allowed_for_repository_group(route, "infra"))
        self.assertFalse(is_allowed_for_repository_group(route, "backend"))

    def test_runtime_context_policy(self) -> None:
        route = resolve_tool_route("graphics_parse_matrix4")
        self.assertTrue(is_allowed_in_runtime_context(route, "read_only_diagnostic"))
        self.assertFalse(is_allowed_in_runtime_context(route, "cloud_worker"))

    def test_explain_tool_policy_mentions_network_default(self) -> None:
        notes = explain_tool_policy(resolve_tool_route("network_data_fetch"))
        self.assertIn("network access denied by default", notes)


if __name__ == "__main__":
    unittest.main()
