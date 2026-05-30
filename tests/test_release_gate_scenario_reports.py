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

from release_gates.scenario_reports import (  # noqa: E402
    append_scenario_report_jsonl,
    build_scenario_report,
    write_scenario_report,
)


class TestReleaseGateScenarioReports(unittest.TestCase):
    def test_writer_writes_only_under_release_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            payload = build_scenario_report({"comparison_id": "cmp_1"}, {"report_id": "r1"}, {"scenario_pack_id": "s1"})
            out = write_scenario_report(payload, path=base / ".release_reports" / "scenario_comparison.json")
            self.assertTrue(out.exists())
            with self.assertRaises(ValueError):
                write_scenario_report(payload, path=base / "not_allowed.json")

    def test_jsonl_appends_valid_json_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            payload = build_scenario_report({"comparison_id": "cmp_1"}, {"report_id": "r1"}, {"scenario_pack_id": "s1"})
            out = append_scenario_report_jsonl(payload, path=base / ".release_reports" / "scenario_comparisons.jsonl")
            self.assertTrue(out.exists())
            lines = out.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 1)
            self.assertEqual(json.loads(lines[0])["comparison"]["comparison_id"], "cmp_1")


if __name__ == "__main__":
    unittest.main()

