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

from repository_intelligence.reports import (  # noqa: E402
    append_repository_intelligence_report_jsonl,
    write_repository_intelligence_report,
    write_timestamped_repository_intelligence_report,
)


class TestRepositoryIntelligenceReports(unittest.TestCase):
    def test_reports_write_under_control_plane_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            report = {"report_id": "r1"}
            out = write_repository_intelligence_report(
                report,
                path=base / ".control_plane" / "repository_intelligence" / "repository_intelligence_report.json",
            )
            self.assertTrue(out.exists())
            self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["report_id"], "r1")
            ts = write_timestamped_repository_intelligence_report(
                report,
                directory=base / ".control_plane" / "repository_intelligence",
            )
            self.assertTrue(ts.exists())
            j = append_repository_intelligence_report_jsonl(
                report,
                path=base / ".control_plane" / "repository_intelligence" / "repository_intelligence_reports.jsonl",
            )
            self.assertTrue(j.exists())


if __name__ == "__main__":
    unittest.main()

