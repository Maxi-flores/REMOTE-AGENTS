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

from repository_governance.contracts import (  # noqa: E402
    create_audit_record,
    create_governance_profile,
    create_health_snapshot,
    validate_audit_record_dict,
    validate_governance_profile_dict,
    validate_health_snapshot_dict,
)


class TestRepositoryGovernanceContracts(unittest.TestCase):
    def test_valid_governance_profile_passes_validation(self) -> None:
        profile = create_governance_profile(
            repository_name="ConceptSHOP",
            repository_group="spa_ui_frontends_vite_react",
            repository_category="Retail",
            status="active",
            risk_tier="high",
            allowed_operations=["read", "git_status"],
            denied_operations=[],
            required_checks=["build", "lint"],
        )
        validate_governance_profile_dict(profile.to_dict())

    def test_invalid_repository_status_fails_validation(self) -> None:
        profile = create_governance_profile(repository_name="ConceptSHOP", repository_group="frontend").to_dict()
        profile["status"] = "ready-ish"
        with self.assertRaises(ValueError):
            validate_governance_profile_dict(profile)

    def test_invalid_risk_tier_fails_validation(self) -> None:
        profile = create_governance_profile(repository_name="ConceptSHOP", repository_group="frontend").to_dict()
        profile["risk_tier"] = "spicy"
        with self.assertRaises(ValueError):
            validate_governance_profile_dict(profile)

    def test_valid_health_snapshot_passes_validation(self) -> None:
        snapshot = create_health_snapshot(
            repository_name="ConceptSHOP",
            status="warning",
            known_risks=["missing eslint config"],
            warnings=["lint not configured"],
        )
        validate_health_snapshot_dict(snapshot.to_dict())

    def test_invalid_health_status_fails_validation(self) -> None:
        snapshot = create_health_snapshot(repository_name="ConceptSHOP").to_dict()
        snapshot["status"] = "sparkly"
        with self.assertRaises(ValueError):
            validate_health_snapshot_dict(snapshot)

    def test_valid_audit_record_passes_validation(self) -> None:
        record = create_audit_record(
            repository_name="ConceptSHOP",
            actor="mission-engine",
            action="evaluate:read",
            operation="read",
            decision="allowed",
            risk_tier="medium",
        )
        validate_audit_record_dict(record.to_dict())

    def test_invalid_audit_decision_fails_validation(self) -> None:
        record = create_audit_record(
            repository_name="ConceptSHOP",
            actor="mission-engine",
            action="evaluate:read",
            operation="read",
            decision="allowed",
            risk_tier="medium",
        ).to_dict()
        record["decision"] = "maybe"
        with self.assertRaises(ValueError):
            validate_audit_record_dict(record)


if __name__ == "__main__":
    unittest.main()
