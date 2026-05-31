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

from governance_recovery.contracts import GovernanceRecoveryPlanReport, new_id, utc_now, validate_governance_recovery_plan_report_dict  # noqa: E402


class TestGovernanceRecoveryContracts(unittest.TestCase):
    def test_contract(self) -> None:
        payload = GovernanceRecoveryPlanReport(
            report_id=new_id("gr"),
            generated_utc=utc_now(),
            source_governance_report_id="g1",
            current_governance_score=50,
            target_governance_score=70,
            actions=[
                {
                    "action_id": "a1",
                    "source_component_id": "c1",
                    "title": "t",
                    "description": "d",
                    "priority": "P1",
                    "expected_score_impact": 10,
                    "target_component": "Portfolio Readiness",
                    "recommended_commands": [],
                    "validation_focus": [],
                    "advisory_only": True,
                    "metadata": {},
                }
            ],
            waves=[
                {
                    "wave_id": "wave_1",
                    "title": "w",
                    "objective": "o",
                    "priority": "P1",
                    "actions": ["a1"],
                    "expected_score_impact": 10,
                    "advisory_only": True,
                    "metadata": {},
                }
            ],
            recommended_sequence=["a1"],
            advisory_only=True,
            metadata={},
        ).to_dict()
        validate_governance_recovery_plan_report_dict(payload)


if __name__ == "__main__":
    unittest.main()

