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

from governance_recovery_dossiers.checklists import (  # noqa: E402
    build_review_checklist,
    build_rollback_guidance,
)


class TestGovernanceRecoveryDossiersChecklists(unittest.TestCase):
    def test_review_checklist_generation(self) -> None:
        checklist = build_review_checklist(
            action={"title": "Resolve drift"},
            target_artifacts=[".control_plane/portfolio_drift/latest.json"],
        )
        self.assertTrue(any("advisory-only" in item.lower() for item in checklist))
        self.assertTrue(any("platform_engine.py" in item for item in checklist))

    def test_rollback_guidance_generation(self) -> None:
        rollback = build_rollback_guidance(target_artifacts=[".control_plane/portfolio_progress/latest.json"])
        self.assertTrue(any("Restore previous state" in item for item in rollback))


if __name__ == "__main__":
    unittest.main()

