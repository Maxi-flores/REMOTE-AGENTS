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

from execution_dossier.checklists import build_review_checklist, build_rollback_guidance  # noqa: E402


class TestExecutionDossierChecklists(unittest.TestCase):
    def test_checklist_and_rollback(self) -> None:
        checklist = build_review_checklist({})
        self.assertGreaterEqual(len(checklist), 3)
        rollback = build_rollback_guidance({"target_files": ["tests/test_x.py", "docs/x.md"]})
        self.assertTrue(any("Revert" in x or "Restore" in x for x in rollback))


if __name__ == "__main__":
    unittest.main()
