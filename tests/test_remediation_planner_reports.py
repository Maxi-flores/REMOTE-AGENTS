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

from remediation_planner.reports import (  # noqa: E402
    append_remediation_plan_report_jsonl,
    write_remediation_plan_report,
    write_timestamped_remediation_plan_report,
)


class TestRemediationPlannerReports(unittest.TestCase):
    def test_writes_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = {"report_id": "r1"}
            latest = write_remediation_plan_report(report, path=root / ".control_plane" / "remediation_plans" / "remediation_plan_report.json")
            self.assertTrue(latest.exists())
            stamped = write_timestamped_remediation_plan_report(report, directory=root / ".control_plane" / "remediation_plans")
            self.assertTrue(stamped.exists())
            history = append_remediation_plan_report_jsonl(report, path=root / ".control_plane" / "remediation_plans" / "remediation_plan_reports.jsonl")
            lines = history.read_text(encoding="utf-8").splitlines()
            self.assertGreaterEqual(len(lines), 1)
            self.assertEqual(json.loads(lines[0])["report_id"], "r1")


if __name__ == "__main__":
    unittest.main()
