import json
import os
import unittest
from pathlib import Path
import sys


_SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from routers.repo_governance_router import resolve_repo_governance_route
from tools.logger import ensure_runtime_directories


class TestRepoGovernanceRouter(unittest.TestCase):
    def setUp(self) -> None:
        ensure_runtime_directories()
        self.errors_file = Path(".logs/errors.json")
        if self.errors_file.exists():
            self.errors_file.unlink()

    def _read_errors(self) -> list[dict]:
        if not self.errors_file.exists():
            return []
        raw = self.errors_file.read_text(encoding="utf-8")
        data = json.loads(raw)
        return data if isinstance(data, list) else []

    def test_known_repository_routes_to_profile(self) -> None:
        route = resolve_repo_governance_route({"instruction": "x", "target_repository": "ConceptSHOP"})
        self.assertFalse(route.used_default_profile)
        self.assertEqual(route.primary_agent_class, "ViteReactPrimaryAgent")
        self.assertEqual(route.twin_agent_class, "ViteReactTwinAgent")
        self.assertEqual(int(route.execution_constraints.get("num_thread")), 4)
        self.assertEqual(int(route.execution_constraints.get("max_context_chars")), 12000)

        self.assertEqual(self._read_errors(), [])

    def test_unknown_repository_falls_back_and_logs(self) -> None:
        route = resolve_repo_governance_route({"instruction": "x", "target_repository": "DoesNotExist"})
        self.assertTrue(route.used_default_profile)
        self.assertEqual(route.primary_agent_class, "RuntimeDiagnosticAgent")
        self.assertEqual(route.twin_agent_class, "RuntimeDiagnosticTwinAgent")

        errors = self._read_errors()
        self.assertGreaterEqual(len(errors), 1)
        self.assertEqual(errors[-1].get("error_type"), "REPO_ROUTER_FALLBACK")

    def test_unmapped_repository_falls_back(self) -> None:
        route = resolve_repo_governance_route({"instruction": "x", "target_repository": "PF-WAI"})
        self.assertTrue(route.used_default_profile)
        self.assertEqual(route.primary_agent_class, "RuntimeDiagnosticAgent")
        self.assertEqual(route.twin_agent_class, "RuntimeDiagnosticTwinAgent")
