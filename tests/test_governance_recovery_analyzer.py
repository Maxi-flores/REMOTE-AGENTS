from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from governance_recovery.analyzer import generate_governance_recovery_plan_report  # noqa: E402


class TestGovernanceRecoveryAnalyzer(unittest.TestCase):
    def test_generates_actions_for_weak_components(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".control_plane" / "portfolio_governance_index").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "portfolio_governance_index" / "latest.json").write_text(
                json.dumps(
                    {
                        "report_id": "g1",
                        "governance_score": 50,
                        "components": [
                            {"component_id": "c1", "name": "Portfolio Readiness", "score": 20},
                            {"component_id": "c2", "name": "Onboarding Coverage", "score": 15},
                            {"component_id": "c3", "name": "Dependency Risk", "score": 40},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            report = generate_governance_recovery_plan_report(base_dir=root)
            self.assertGreater(len(report["actions"]), 0)
            self.assertGreaterEqual(report["target_governance_score"], report["current_governance_score"])


if __name__ == "__main__":
    unittest.main()

