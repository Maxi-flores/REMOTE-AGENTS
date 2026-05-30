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

from release_gates.rollback import build_rollback_precheck  # noqa: E402


class TestReleasePromotionRollback(unittest.TestCase):
    def test_rollback_precheck_includes_required_artifacts_and_steps(self) -> None:
        precheck = build_rollback_precheck(
            {"aggregate_decision": "blocked", "blockers": ["b1"]},
            "production",
        )
        self.assertTrue(precheck["required_artifacts"])
        self.assertTrue(precheck["recommended_steps"])
        self.assertIn("target_environment", precheck)


if __name__ == "__main__":
    unittest.main()

