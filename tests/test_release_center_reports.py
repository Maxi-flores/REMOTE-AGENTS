from __future__ import annotations

import json
import os
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

from release_center.reports import (  # noqa: E402
    append_release_timeline_report_jsonl,
    build_release_timeline_report,
    write_release_timeline_report,
)


class TestReleaseCenterReports(unittest.TestCase):
    def test_report_writer_writes_only_under_release_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            rr = base / ".release_reports"
            rr.mkdir(parents=True, exist_ok=True)
            (rr / "release_readiness.json").write_text(
                json.dumps({"readiness_status": "ready", "readiness_score": 90}),
                encoding="utf-8",
            )
            cwd = Path.cwd()
            try:
                os.chdir(base)
                report = build_release_timeline_report()
            finally:
                os.chdir(cwd)
            out = write_release_timeline_report(report, path=rr / "release_timeline.json")
            self.assertTrue(out.exists())
            with self.assertRaises(ValueError):
                write_release_timeline_report(report, path=base / "nope.json")

    def test_jsonl_appends_valid_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            report = {
                "report_id": "r1",
                "generated_utc": "2026-05-29T00:00:00Z",
                "release_label": "x",
                "timeline_events": [],
                "milestones": [],
                "summary": {},
                "escalation_hints": [],
                "advisory_only": True,
                "metadata": {},
            }
            out = append_release_timeline_report_jsonl(report, path=base / ".release_reports" / "release_timeline.jsonl")
            lines = out.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 1)
            self.assertEqual(json.loads(lines[0])["report_id"], "r1")


if __name__ == "__main__":
    unittest.main()

