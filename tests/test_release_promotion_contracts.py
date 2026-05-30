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

from release_gates.promotion_contracts import (  # noqa: E402
    PromotionProfile,
    PromotionRecommendation,
    validate_promotion_profile_dict,
    validate_promotion_recommendation_dict,
)


class TestReleasePromotionContracts(unittest.TestCase):
    def test_valid_profile_passes(self) -> None:
        payload = PromotionProfile(
            profile_id="dev_promotion_profile",
            display_name="Dev",
            target_environment="dev",
            required_scenario_pack="default_release_scenarios",
            minimum_aggregate_status="review_required",
            allowed_aggregate_decisions=["pass", "pass_with_warnings", "mixed"],
            require_no_blockers=False,
            require_rollback_plan=False,
            require_ci_handoff=False,
            max_warning_count=100,
            max_error_count=10,
            advisory_only=True,
            metadata={},
        ).to_dict()
        validate_promotion_profile_dict(payload)

    def test_invalid_environment_fails(self) -> None:
        payload = {
            "profile_id": "bad",
            "display_name": "Bad",
            "target_environment": "prod",
            "required_scenario_pack": "default_release_scenarios",
            "minimum_aggregate_status": "ready",
            "allowed_aggregate_decisions": ["pass"],
            "require_no_blockers": True,
            "require_rollback_plan": True,
            "require_ci_handoff": True,
            "max_warning_count": 0,
            "max_error_count": 0,
            "advisory_only": True,
            "metadata": {},
        }
        with self.assertRaises(ValueError):
            validate_promotion_profile_dict(payload)

    def test_valid_recommendation_passes(self) -> None:
        payload = PromotionRecommendation(
            recommendation_id="r1",
            profile_id="dev_promotion_profile",
            target_environment="dev",
            scenario_pack_id="default_release_scenarios",
            source_comparison_id="c1",
            recommendation="promote_with_warnings",
            confidence="medium",
            reasons=["ok"],
            blockers=[],
            warnings=["w1"],
            rollback_precheck={"target_environment": "dev"},
            ci_handoff={"target_environment": "dev"},
            created_utc="2026-05-29T00:00:00Z",
            advisory_only=True,
            metadata={},
        ).to_dict()
        validate_promotion_recommendation_dict(payload)

    def test_invalid_recommendation_fails(self) -> None:
        payload = {
            "recommendation_id": "r1",
            "profile_id": "dev_promotion_profile",
            "target_environment": "dev",
            "recommendation": "ship_it",
            "confidence": "high",
            "reasons": [],
            "blockers": [],
            "warnings": [],
            "rollback_precheck": {},
            "ci_handoff": {},
            "created_utc": "2026-05-29T00:00:00Z",
            "advisory_only": True,
            "metadata": {},
        }
        with self.assertRaises(ValueError):
            validate_promotion_recommendation_dict(payload)


if __name__ == "__main__":
    unittest.main()

