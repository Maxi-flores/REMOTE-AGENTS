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

from release_gates.scenario_contracts import (  # noqa: E402
    ScenarioComparisonResult,
    ScenarioPack,
    validate_scenario_comparison_result_dict,
    validate_scenario_pack_dict,
)


class TestReleaseGateScenarioContracts(unittest.TestCase):
    def test_valid_scenario_pack_passes(self) -> None:
        payload = ScenarioPack(
            scenario_pack_id="default_release_scenarios",
            display_name="Default",
            policy_names=["default_gate_policy", "strict_gate_policy"],
            comparison_strategy="compare_all",
            advisory_only=True,
            metadata={},
        ).to_dict()
        validate_scenario_pack_dict(payload)

    def test_invalid_comparison_strategy_fails(self) -> None:
        payload = {
            "scenario_pack_id": "bad",
            "display_name": "Bad",
            "policy_names": ["default_gate_policy"],
            "comparison_strategy": "not_real",
            "advisory_only": True,
            "metadata": {},
        }
        with self.assertRaises(ValueError):
            validate_scenario_pack_dict(payload)

    def test_valid_scenario_comparison_result_passes(self) -> None:
        payload = ScenarioComparisonResult(
            comparison_id="cmp_1",
            scenario_pack_id="default_release_scenarios",
            report_id="r1",
            generated_utc="2026-05-29T00:00:00Z",
            comparison_strategy="compare_all",
            policy_decisions=[],
            aggregate_decision="mixed",
            aggregate_status="review_required",
            blockers=[],
            warnings=[],
            summary={},
            advisory_only=True,
            metadata={},
        ).to_dict()
        validate_scenario_comparison_result_dict(payload)

    def test_invalid_aggregate_decision_fails(self) -> None:
        payload = {
            "comparison_id": "cmp_1",
            "scenario_pack_id": "default_release_scenarios",
            "generated_utc": "2026-05-29T00:00:00Z",
            "comparison_strategy": "compare_all",
            "policy_decisions": [],
            "aggregate_decision": "maybe",
            "aggregate_status": "review_required",
            "blockers": [],
            "warnings": [],
            "summary": {},
            "advisory_only": True,
            "metadata": {},
        }
        with self.assertRaises(ValueError):
            validate_scenario_comparison_result_dict(payload)


if __name__ == "__main__":
    unittest.main()

