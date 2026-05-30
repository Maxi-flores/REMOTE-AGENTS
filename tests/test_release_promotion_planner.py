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

from release_gates.promotion_loader import load_named_promotion_profile  # noqa: E402
from release_gates.promotion_planner import plan_promotion  # noqa: E402


def _comparison(
    *,
    status: str = "ready",
    decision: str = "pass",
    blockers: list[str] | None = None,
    warnings: list[str] | None = None,
    scenario_pack_id: str = "default_release_scenarios",
) -> dict:
    return {
        "comparison_id": "cmp_1",
        "scenario_pack_id": scenario_pack_id,
        "aggregate_status": status,
        "aggregate_decision": decision,
        "blockers": blockers or [],
        "warnings": warnings or [],
        "summary": {"decision_counts": {"blocked": 0}},
        "policy_decisions": [],
    }


class TestReleasePromotionPlanner(unittest.TestCase):
    def test_planner_promotes_clean_dev(self) -> None:
        profile = load_named_promotion_profile("dev_promotion_profile", REPO_ROOT / "config" / "release_gates" / "promotion_profiles")
        rec = plan_promotion(_comparison(), profile)
        self.assertEqual(rec["recommendation"], "promote")

    def test_planner_blocks_production_with_blockers(self) -> None:
        profile = load_named_promotion_profile("production_promotion_profile", REPO_ROOT / "config" / "release_gates" / "promotion_profiles")
        rec = plan_promotion(
            _comparison(blockers=["b1"], scenario_pack_id="production_release_scenarios"),
            profile,
        )
        self.assertEqual(rec["recommendation"], "blocked")

    def test_planner_promote_with_warnings_for_staging_warning_only(self) -> None:
        profile = load_named_promotion_profile("staging_promotion_profile", REPO_ROOT / "config" / "release_gates" / "promotion_profiles")
        rec = plan_promotion(
            _comparison(
                status="review_required",
                decision="pass_with_warnings",
                warnings=["w1"],
                scenario_pack_id="production_release_scenarios",
            ),
            profile,
        )
        self.assertEqual(rec["recommendation"], "promote_with_warnings")

    def test_planner_hold_or_unknown_for_incomplete_input(self) -> None:
        profile = load_named_promotion_profile("dev_promotion_profile", REPO_ROOT / "config" / "release_gates" / "promotion_profiles")
        rec = plan_promotion({"aggregate_status": "unknown"}, profile)
        self.assertIn(rec["recommendation"], {"hold", "unknown", "blocked"})


if __name__ == "__main__":
    unittest.main()

