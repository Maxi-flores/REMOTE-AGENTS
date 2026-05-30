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

from lifecycle_manager.capability_contracts import AgentCapabilityProfile, validate_capability_profile_dict  # noqa: E402


class TestLifecycleCapabilityContracts(unittest.TestCase):
    def _base(self) -> dict:
        return AgentCapabilityProfile(
            capability_profile_id="cp1",
            agent_class="A1",
            display_name="Agent One",
            category="execution",
            repositories=[],
            repository_groups=[],
            capabilities=[],
            allowed_tools=[],
            denied_tools=[],
            risk_tier="medium",
            primary_roles=[],
            secondary_roles=[],
            health_requirements={},
            performance_metrics={},
            status="active",
            created_utc="2026-05-29T00:00:00Z",
            updated_utc="2026-05-29T00:00:00Z",
            metadata={},
        ).to_dict()

    def test_valid_profile_passes(self) -> None:
        validate_capability_profile_dict(self._base())

    def test_invalid_status_fails(self) -> None:
        p = self._base()
        p["status"] = "bad"
        with self.assertRaises(ValueError):
            validate_capability_profile_dict(p)

    def test_invalid_risk_tier_fails(self) -> None:
        p = self._base()
        p["risk_tier"] = "bad"
        with self.assertRaises(ValueError):
            validate_capability_profile_dict(p)


if __name__ == "__main__":
    unittest.main()

