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

from repository_governance.contracts import create_governance_profile  # noqa: E402
from repository_governance.policies import (  # noqa: E402
    evaluate_repository_operation,
    explain_governance_decision,
    is_operation_allowed,
    requires_approval,
)


class TestRepositoryGovernancePolicies(unittest.TestCase):
    def test_policy_allows_safe_read_operations(self) -> None:
        profile = create_governance_profile(repository_name="ConceptSHOP", repository_group="frontend")
        for operation in ("read", "git_status", "git_diff"):
            with self.subTest(operation=operation):
                record = evaluate_repository_operation(profile, operation, actor="tester")
                self.assertTrue(is_operation_allowed(profile, operation))
                self.assertEqual(record.decision, "allowed")

    def test_policy_requires_approval_for_sensitive_operations(self) -> None:
        profile = create_governance_profile(repository_name="ConceptSHOP", repository_group="frontend")
        for operation in ("write", "deploy", "network_fetch", "shell_command", "git_commit", "git_push"):
            with self.subTest(operation=operation):
                self.assertTrue(requires_approval(profile, operation))
                record = evaluate_repository_operation(profile, operation, actor="tester")
                self.assertEqual(record.decision, "needs_approval")

    def test_denied_operations_are_denied(self) -> None:
        profile = create_governance_profile(
            repository_name="ConceptSHOP",
            repository_group="frontend",
            denied_operations=["deploy"],
        )
        record = evaluate_repository_operation(profile, "deploy", actor="tester")
        self.assertFalse(is_operation_allowed(profile, "deploy"))
        self.assertEqual(record.decision, "denied")

    def test_unknown_operations_return_needs_review(self) -> None:
        profile = create_governance_profile(repository_name="ConceptSHOP", repository_group="frontend")
        record = evaluate_repository_operation(profile, "rewrite_history", actor="tester")
        self.assertEqual(record.decision, "needs_review")
        self.assertIn("needs_review", explain_governance_decision(record))

    def test_high_risk_profiles_prefer_approval_for_non_safe_operations(self) -> None:
        profile = create_governance_profile(
            repository_name="ConceptSHOP",
            repository_group="frontend",
            risk_tier="high",
            approval_policy={"required_for_risk_tiers": ["high", "critical"]},
        )
        record = evaluate_repository_operation(profile, "build", actor="tester")
        self.assertEqual(record.decision, "needs_approval")


if __name__ == "__main__":
    unittest.main()
