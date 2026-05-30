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

from release_gates.promotion_reports import (  # noqa: E402
    append_promotion_report_jsonl,
    build_promotion_report,
    write_promotion_report,
)


class TestReleasePromotionReports(unittest.TestCase):
    def test_writer_writes_only_under_release_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            report = build_promotion_report([{"recommendation_id": "r1"}], None)
            out = write_promotion_report(report, path=base / ".release_reports" / "promotion_recommendations.json")
            self.assertTrue(out.exists())
            with self.assertRaises(ValueError):
                write_promotion_report(report, path=base / "not_allowed.json")

    def test_jsonl_appends_valid_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            report = build_promotion_report([{"recommendation_id": "r1"}], None)
            out = append_promotion_report_jsonl(
                report,
                path=base / ".release_reports" / "promotion_recommendations.jsonl",
            )
            lines = out.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 1)
            payload = json.loads(lines[0])
            self.assertIn("recommendations", payload)


if __name__ == "__main__":
    unittest.main()

