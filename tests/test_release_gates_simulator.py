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

from release_gates.policy_loader import load_named_gate_policy  # noqa: E402
from release_gates.simulator import simulate_gate  # noqa: E402


def _report(score: float, findings: list[dict] | None = None, warnings: list[str] | None = None, checked: list[dict] | None = None) -> dict:
    return {
        "report_id": "r1",
        "readiness_score": score,
        "blockers": [],
        "warnings": warnings or [],
        "findings": findings or [],
        "checked_artifacts": checked
        or [
            {"artifact_type": "control_plane_snapshot"},
            {"artifact_type": "sentient_ui_view_model"},
        ],
    }


class TestReleaseGatesSimulator(unittest.TestCase):
    def test_simulator_passes_clean_report(self) -> None:
        policy = load_named_gate_policy("default_gate_policy", REPO_ROOT / "config" / "release_gates")
        decision = simulate_gate(_report(95), policy)
        self.assertEqual(decision["decision"], "pass")

    def test_simulator_pass_with_warnings(self) -> None:
        policy = load_named_gate_policy("default_gate_policy", REPO_ROOT / "config" / "release_gates")
        decision = simulate_gate(_report(90, warnings=["w1"]), policy)
        self.assertEqual(decision["decision"], "pass_with_warnings")

    def test_simulator_blocks_low_score(self) -> None:
        policy = load_named_gate_policy("default_gate_policy", REPO_ROOT / "config" / "release_gates")
        decision = simulate_gate(_report(60), policy)
        self.assertEqual(decision["decision"], "blocked")

    def test_simulator_blocks_critical_when_required(self) -> None:
        policy = load_named_gate_policy("default_gate_policy", REPO_ROOT / "config" / "release_gates")
        decision = simulate_gate(
            _report(95, findings=[{"severity": "critical", "drift_type": "unsupported_version", "message": "x"}]),
            policy,
        )
        self.assertEqual(decision["decision"], "blocked")

    def test_simulator_blocks_missing_required_artifacts(self) -> None:
        policy = load_named_gate_policy("default_gate_policy", REPO_ROOT / "config" / "release_gates")
        decision = simulate_gate(_report(95, checked=[{"artifact_type": "control_plane_snapshot"}]), policy)
        self.assertEqual(decision["decision"], "blocked")

    def test_simulator_respects_experimental_permissive_policy(self) -> None:
        policy = load_named_gate_policy("experimental_gate_policy", REPO_ROOT / "config" / "release_gates")
        decision = simulate_gate(
            _report(60, findings=[{"severity": "critical", "drift_type": "unsupported_version", "message": "x"}], checked=[]),
            policy,
        )
        self.assertIn(decision["decision"], {"unknown", "pass_with_warnings", "pass"})


if __name__ == "__main__":
    unittest.main()

