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


class TestRemediationPlannerStrategicIntegration(unittest.TestCase):
    def test_strategic_includes_remediation_candidates_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".control_plane" / "executive").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "remediation_plans").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "executive" / "executive_briefing.json").write_text(
                json.dumps({"overall_status": "healthy", "top_risks": [], "recommended_actions": []}),
                encoding="utf-8",
            )
            (root / ".control_plane" / "remediation_plans" / "remediation_plan_report.json").write_text(
                json.dumps(
                    {
                        "batches": [
                            {"batch_id": "b1", "name": "P1 remediation batch", "priority": "P1", "repository": "REMOTE-AGENTS", "item_ids": ["i1"], "expected_risk_reduction": 80, "estimated_total_effort": 40}
                        ]
                    }
                ),
                encoding="utf-8",
            )
            report = generate_strategic_mission_report(base_dir=root)
            self.assertTrue(any("remediation" in str(c.get("title", "")).lower() for c in report["candidates"]))


if __name__ == "__main__":
    unittest.main()
