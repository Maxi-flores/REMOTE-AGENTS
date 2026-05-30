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

from release_gates.ci_handoff import build_ci_handoff_artifact  # noqa: E402


class TestReleasePromotionCiHandoff(unittest.TestCase):
    def test_ci_handoff_includes_checks_and_stage(self) -> None:
        artifact = build_ci_handoff_artifact(
            {"target_environment": "staging", "recommendation": "promote_with_warnings"},
            {"aggregate_decision": "pass_with_warnings"},
        )
        self.assertTrue(artifact["recommended_checks"])
        self.assertIn("suggested_pipeline_stage", artifact)
        self.assertEqual(artifact["promotion_recommendation"], "promote_with_warnings")


if __name__ == "__main__":
    unittest.main()

