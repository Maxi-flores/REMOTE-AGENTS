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

from release_gates.contracts import (  # noqa: E402
    GateDecision,
    GatePolicy,
    validate_gate_decision_dict,
    validate_gate_policy_dict,
)


class TestReleaseGatesContracts(unittest.TestCase):
    def test_valid_gate_policy_passes_validation(self) -> None:
        payload = GatePolicy(
            policy_id="default_gate_policy",
            display_name="Default",
            minimum_readiness_score=80,
            block_on_critical_findings=True,
            block_on_malformed_artifacts=True,
            block_on_missing_artifacts=True,
            block_on_unsupported_versions=True,
            max_warning_count=10,
            max_error_count=3,
            required_artifacts=["control_plane_snapshot"],
            advisory_only=True,
        ).to_dict()
        validate_gate_policy_dict(payload)

    def test_invalid_threshold_fails_validation(self) -> None:
        payload = GatePolicy(
            policy_id="default_gate_policy",
            display_name="Default",
            minimum_readiness_score=120,
            block_on_critical_findings=True,
            block_on_malformed_artifacts=True,
            block_on_missing_artifacts=True,
            block_on_unsupported_versions=True,
            max_warning_count=10,
            max_error_count=3,
            required_artifacts=[],
            advisory_only=True,
        ).to_dict()
        with self.assertRaises(ValueError):
            validate_gate_policy_dict(payload)

    def test_valid_gate_decision_passes_validation(self) -> None:
        payload = GateDecision(
            decision_id="d1",
            policy_id="default_gate_policy",
            decision="pass",
            readiness_score=92,
            blockers=[],
            warnings=[],
            evaluated_artifacts=[],
            advisory_only=True,
        ).to_dict()
        validate_gate_decision_dict(payload)

    def test_invalid_decision_fails_validation(self) -> None:
        payload = GateDecision(
            decision_id="d1",
            policy_id="default_gate_policy",
            decision="pass",
            readiness_score=92,
            blockers=[],
            warnings=[],
            evaluated_artifacts=[],
            advisory_only=True,
        ).to_dict()
        payload["decision"] = "ship_it"
        with self.assertRaises(ValueError):
            validate_gate_decision_dict(payload)


if __name__ == "__main__":
    unittest.main()

