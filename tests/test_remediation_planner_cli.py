from __future__ import annotations

import io
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

from remediation_planner.cli import main  # noqa: E402


class TestRemediationPlannerCli(unittest.TestCase):
    def test_print_and_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rie_dir = root / ".control_plane" / "repository_intelligence"
            rie_dir.mkdir(parents=True, exist_ok=True)
            (rie_dir / "repository_intelligence_report.json").write_text(
                json.dumps({"report_id": "r1", "repository_name": "tmp", "overall_status": "warning", "findings": []}),
                encoding="utf-8",
            )
            stdout = io.StringIO()
            rc = main(["--print", "--export", "--export-jsonl", "--base-dir", str(root)], stdout=stdout)
            self.assertEqual(rc, 0)
            self.assertIn("Repository Remediation Plan", stdout.getvalue())
            self.assertTrue((root / ".control_plane" / "remediation_plans" / "remediation_plan_report.json").exists())


if __name__ == "__main__":
    unittest.main()
