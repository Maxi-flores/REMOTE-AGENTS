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

from release_gates.multi_simulator import (  # noqa: E402
    aggregate_policy_decisions,
    simulate_scenario_pack,
)
from release_gates.scenario_loader import load_named_scenario_pack  # noqa: E402


def _report(score: float, *, findings: list[dict] | None = None, warnings: list[str] | None = None) -> dict:
    return {
        "report_id": "r1",
        "readiness_score": score,
        "blockers": [],
        "warnings": warnings or [],
        "findings": findings or [],
        "checked_artifacts": [
            {"artifact_type": "control_plane_snapshot"},
            {"artifact_type": "sentient_ui_view_model"},
        ],
        "readiness_status": "ready",
    }


class TestReleaseGateMultiSimulator(unittest.TestCase):
    def test_simulate_returns_one_decision_per_policy(self) -> None:
        pack = load_named_scenario_pack("default_release_scenarios", REPO_ROOT / "config" / "release_gates" / "scenario_packs")
        result = simulate_scenario_pack(_report(95), pack)
        self.assertEqual(len(result["policy_decisions"]), len(pack["policy_names"]))

    def test_compare_all_returns_mixed_when_policies_disagree(self) -> None:
        decisions = [{"decision": "pass"}, {"decision": "blocked"}]
        aggregate, _, _ = aggregate_policy_decisions(decisions, "compare_all")
        self.assertEqual(aggregate, "mixed")

    def test_strictest_wins_blocks_if_any_blocks(self) -> None:
        decisions = [{"decision": "pass"}, {"decision": "blocked"}]
        aggregate, _, _ = aggregate_policy_decisions(decisions, "strictest_wins")
        self.assertEqual(aggregate, "blocked")

    def test_permissive_preview_preserves_strict_blockers_as_warnings(self) -> None:
        decisions = [{"decision": "pass", "blockers": ["strict says no"], "warnings": []}]
        aggregate, _, warnings = aggregate_policy_decisions(decisions, "permissive_preview")
        self.assertEqual(aggregate, "pass")
        self.assertIn("strict says no", warnings)

    def test_production_candidate_blocks_if_strict_blocks(self) -> None:
        decisions = [
            {"policy_name": "default_gate_policy", "policy_id": "default_gate_policy", "decision": "pass"},
            {"policy_name": "strict_gate_policy", "policy_id": "strict_gate_policy", "decision": "blocked"},
        ]
        aggregate, _, _ = aggregate_policy_decisions(decisions, "production_candidate")
        self.assertEqual(aggregate, "blocked")


if __name__ == "__main__":
    unittest.main()

