from __future__ import annotations

import json
import shutil
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

from control_plane.bootstrap import bootstrap_advisory_artifacts  # noqa: E402
from executive_briefing.briefing_builder import build_executive_briefing  # noqa: E402
from lifecycle_manager.bootstrap import seed_lifecycle_capabilities  # noqa: E402
from lifecycle_manager.capability_contracts import validate_capability_profile_dict  # noqa: E402
from lifecycle_manager.lifecycle_contracts import validate_lifecycle_state_dict  # noqa: E402


class TestLifecycleBootstrap(unittest.TestCase):
    def test_seed_generates_non_empty_profiles_and_states(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _prepare_workspace(base)
            result = seed_lifecycle_capabilities(base)
            self.assertGreater(result["capability_profiles_total"], 0)
            self.assertGreater(result["lifecycle_states_total"], 0)

            state = json.loads((base / ".lifecycle" / "agents.json").read_text(encoding="utf-8"))
            profiles = state.get("capability_profiles", {})
            lifecycle_states = state.get("lifecycle_states", {})
            self.assertTrue(isinstance(profiles, dict) and len(profiles) > 0)
            self.assertTrue(isinstance(lifecycle_states, dict) and len(lifecycle_states) > 0)
            for payload in profiles.values():
                if isinstance(payload, dict):
                    validate_capability_profile_dict(payload)
            for payload in lifecycle_states.values():
                if isinstance(payload, dict):
                    validate_lifecycle_state_dict(payload)

    def test_seed_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _prepare_workspace(base)
            first = seed_lifecycle_capabilities(base)
            second = seed_lifecycle_capabilities(base)
            self.assertEqual(first["capability_profiles_total"], second["capability_profiles_total"])
            self.assertEqual(first["lifecycle_states_total"], second["lifecycle_states_total"])

    def test_executive_briefing_improves_after_seed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _prepare_workspace(base)
            _write_all_ok_orchestration_report(base)
            before = build_executive_briefing(base_dir=base)
            self.assertEqual(before["overall_status"], "degraded")
            seed_lifecycle_capabilities(base)
            after = build_executive_briefing(base_dir=base)
            self.assertIn(after["overall_status"], {"healthy", "warning"})


def _prepare_workspace(base: Path) -> None:
    bootstrap_advisory_artifacts(base)
    (base / "config" / "registries").mkdir(parents=True, exist_ok=True)
    shutil.copy2(REPO_ROOT / "config" / "registries" / "agents.json", base / "config" / "registries" / "agents.json")
    shutil.copy2(REPO_ROOT / "config" / "registries" / "repositories.json", base / "config" / "registries" / "repositories.json")
    shutil.copy2(REPO_ROOT / "config" / "registries" / "tools.json", base / "config" / "registries" / "tools.json")
    shutil.copy2(REPO_ROOT / "config" / "agent_registry.json", base / "config" / "agent_registry.json")


def _write_all_ok_orchestration_report(base: Path) -> None:
    stage_names = [
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
    ]
    report = {
        "report_id": "r1",
        "orchestration_id": "o1",
        "generated_utc": "2026-01-01T00:00:00Z",
        "pipeline_status": "ok",
        "stage_results": [
            {
                "stage_name": name,
                "status": "ok",
                "input_refs": [],
                "output_refs": [],
                "warnings": [],
                "blockers": [],
                "summary": {},
                "completed_utc": "2026-01-01T00:00:00Z",
                "advisory_only": True,
                "metadata": {},
            }
            for name in stage_names
        ],
        "cross_stage_findings": [],
        "recommended_next_actions": [],
        "advisory_only": True,
        "metadata": {},
    }
    (base / ".control_plane" / "orchestration").mkdir(parents=True, exist_ok=True)
    (base / ".control_plane" / "orchestration" / "orchestration_report.json").write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()

