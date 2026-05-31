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

from work_queue_manager.scoring import (  # noqa: E402
    compute_effort_score,
    compute_readiness_score,
    compute_risk_score,
    execution_readiness_from_score,
)


class TestWorkQueueScoring(unittest.TestCase):
    def test_scoring(self) -> None:
        pkg = {"estimated_scope": "small", "target_files": ["a.py"], "validation_commands": ["x"], "risk_level": "low"}
        effort = compute_effort_score(pkg)
        risk = compute_risk_score(pkg)
        readiness = compute_readiness_score(risk_score=risk, dependency_count=0, blocker_count=0, effort_score=effort, subsystem_concentration=1)
        self.assertTrue(0 <= readiness <= 100)
        self.assertIn(execution_readiness_from_score(readiness), {"ready", "waiting", "blocked", "deferred"})


if __name__ == "__main__":
    unittest.main()
