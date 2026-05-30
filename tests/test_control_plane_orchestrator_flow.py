from __future__ import annotations

import json
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

from control_plane.orchestrator import STAGE_ORDER, create_orchestration_request, run_orchestration  # noqa: E402


class TestControlPlaneOrchestratorFlow(unittest.TestCase):
    def test_stage_order_exact(self) -> None:
        self.assertEqual(
            STAGE_ORDER,
            [
                "mission",
                "scheduler",
                "tool_router",
                "governance",
                "memory_graph",
                "release_readiness",
                "release_gates",
                "release_center",
                "lifecycle",
                "snapshot",
                "sentient_ui",
            ],
        )

    def test_missing_artifacts_warn_not_crash(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            request = create_orchestration_request(trigger_source="manual")
            report = run_orchestration(request, base_dir=tmp)
            self.assertTrue(report["advisory_only"])
            self.assertEqual(len(report["stage_results"]), len(STAGE_ORDER))
            statuses = {s["status"] for s in report["stage_results"]}
            self.assertIn("not_run", statuses)

    def test_existing_artifacts_produce_ok_or_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / ".missions").mkdir(parents=True)
            (base / ".scheduler").mkdir(parents=True)
            (base / ".scheduler" / "state.json").write_text(
                json.dumps({"schema_version": 1, "workers": {}, "leases": {}, "scheduler_events": []}),
                encoding="utf-8",
            )
            (base / "config" / "registries").mkdir(parents=True)
            (base / "config" / "registries" / "tools.json").write_text(
                json.dumps({"tools": []}),
                encoding="utf-8",
            )
            (base / "config" / "platform_mcp_tools.json").write_text(json.dumps({"tools": []}), encoding="utf-8")
            request = create_orchestration_request(trigger_source="manual")
            report = run_orchestration(request, base_dir=tmp)
            by_stage = {s["stage_name"]: s for s in report["stage_results"]}
            self.assertIn(by_stage["mission"]["status"], {"ok", "warning"})
            self.assertIn(by_stage["scheduler"]["status"], {"ok", "warning"})
            self.assertIn(by_stage["tool_router"]["status"], {"ok", "warning"})


if __name__ == "__main__":
    unittest.main()

