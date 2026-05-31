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

from remediation_planner.planner import generate_remediation_plan_report  # noqa: E402


class TestRemediationPlannerGeneration(unittest.TestCase):
    def test_generates_from_rie_report(self) -> None:
        rie = {
            "report_id": "rie1",
            "repository_name": "REMOTE-AGENTS",
            "overall_status": "degraded",
            "findings": [
                {
                    "finding_id": "f1",
                    "severity": "high",
                    "category": "governance",
                    "title": "Governance issue",
                    "description": "desc",
                    "recommended_action": "fix it",
                }
            ],
        }
        report = generate_remediation_plan_report(rie_report=rie)
        self.assertGreaterEqual(len(report["items"]), 1)
        self.assertGreaterEqual(len(report["batches"]), 1)

    def test_reads_default_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / ".control_plane" / "repository_intelligence"
            target.mkdir(parents=True, exist_ok=True)
            (target / "repository_intelligence_report.json").write_text(
                json.dumps({"report_id": "r1", "repository_name": "tmp", "overall_status": "healthy", "findings": []}),
                encoding="utf-8",
            )
            report = generate_remediation_plan_report(base_dir=root)
            self.assertIn("report_id", report)


if __name__ == "__main__":
    unittest.main()
