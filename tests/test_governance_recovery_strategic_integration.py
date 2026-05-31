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

from strategic_missions.generator import generate_strategic_mission_report  # noqa: E402


class TestGovernanceRecoveryStrategicIntegration(unittest.TestCase):
    def test_recovery_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".control_plane" / "governance_recovery").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "governance_recovery" / "latest.json").write_text(
                json.dumps(
                    {
                        "actions": [
                            {
                                "action_id": "a1",
                                "title": "Fix onboarding",
                                "description": "Do it",
                                "priority": "P1",
                                "expected_score_impact": 10,
                                "target_component": "Onboarding Coverage",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            report = generate_strategic_mission_report(
                briefing={"overall_status": "healthy", "top_risks": [], "recommended_actions": []},
                base_dir=root,
            )
            titles = [str(c.get("title") or "") for c in report.get("candidates", []) if isinstance(c, dict)]
            self.assertTrue(any("Recovery action" in t for t in titles))


if __name__ == "__main__":
    unittest.main()

