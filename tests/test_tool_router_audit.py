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

from tool_router.audit import build_tool_route_audit_record  # noqa: E402
from tool_router.router import resolve_tool_route  # noqa: E402


class TestToolRouterAudit(unittest.TestCase):
    def test_audit_formatter_creates_required_fields(self) -> None:
        route = resolve_tool_route("workspace_file_router")
        record = build_tool_route_audit_record(
            route,
            requested_by="mission-engine",
            repository_name="ConceptSHOP",
            mission_id="mission_123",
            task_id="task_456",
        )
        self.assertTrue(record["audit_id"].startswith("tool_audit_"))
        self.assertEqual(record["tool_name"], "workspace_file_router")
        self.assertEqual(record["provider"], route.provider)
        self.assertEqual(record["risk_tier"], "high")
        self.assertTrue(record["approval_required"])
        self.assertEqual(record["repository_name"], "ConceptSHOP")
        self.assertEqual(record["mission_id"], "mission_123")
        self.assertEqual(record["task_id"], "task_456")
        self.assertEqual(record["requested_by"], "mission-engine")
        self.assertIsInstance(record["created_utc"], str)
        self.assertIsInstance(record["metadata"], dict)


if __name__ == "__main__":
    unittest.main()
