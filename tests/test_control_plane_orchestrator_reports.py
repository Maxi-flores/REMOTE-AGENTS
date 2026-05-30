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

from control_plane.orchestrator_reports import (  # noqa: E402
    append_orchestration_report_jsonl,
    write_orchestration_report,
)


class TestControlPlaneOrchestratorReports(unittest.TestCase):
    def test_write_report_under_control_plane_orchestration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            report = {"report_id": "r1"}
            out = write_orchestration_report(report, path=base / ".control_plane" / "orchestration" / "a.json")
            self.assertTrue(out.exists())
            self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["report_id"], "r1")

    def test_append_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            out = append_orchestration_report_jsonl(
                {"report_id": "r2"},
                path=base / ".control_plane" / "orchestration" / "a.jsonl",
            )
            lines = out.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 1)
            self.assertEqual(json.loads(lines[0])["report_id"], "r2")

    def test_rejects_write_outside_allowed_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            with self.assertRaises(ValueError):
                write_orchestration_report({"report_id": "r3"}, path=base / "bad.json")


if __name__ == "__main__":
    unittest.main()

