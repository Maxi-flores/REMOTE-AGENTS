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

from tool_router.contracts import ToolRoute, validate_tool_route_dict  # noqa: E402


class TestToolRouteContracts(unittest.TestCase):
    def test_valid_tool_route_passes_validation(self) -> None:
        route = ToolRoute(
            tool_name="workspace_file_router",
            provider="mcp",
            implementation_status="active",
            risk_tier="high",
            approval_required=True,
            allowed_runtime_contexts=["local_worker"],
            metadata={"description": "Read/write files"},
        )
        payload = route.to_dict()
        validate_tool_route_dict(payload)
        restored = ToolRoute.from_dict(payload)
        self.assertEqual(restored.tool_name, "workspace_file_router")
        self.assertEqual(restored.provider, "mcp")

    def test_invalid_provider_fails_validation(self) -> None:
        route = ToolRoute(
            tool_name="bad_tool",
            provider="mcp",
            implementation_status="active",
            risk_tier="low",
            approval_required=False,
        ).to_dict()
        route["provider"] = "mystery_provider"
        with self.assertRaises(ValueError):
            validate_tool_route_dict(route)

    def test_invalid_risk_tier_fails_validation(self) -> None:
        route = ToolRoute(
            tool_name="bad_tool",
            provider="mcp",
            implementation_status="active",
            risk_tier="low",
            approval_required=False,
        ).to_dict()
        route["risk_tier"] = "spicy"
        with self.assertRaises(ValueError):
            validate_tool_route_dict(route)


if __name__ == "__main__":
    unittest.main()
