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

from work_queue_manager.reports import append_work_queue_report_jsonl, write_timestamped_work_queue_report, write_work_queue_report  # noqa: E402


class TestWorkQueueReports(unittest.TestCase):
    def test_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = {"report_id": "x"}
            a = write_work_queue_report(report, path=root / ".control_plane" / "work_queue" / "latest.json")
            b = write_timestamped_work_queue_report(report, directory=root / ".control_plane" / "work_queue")
            c = append_work_queue_report_jsonl(report, path=root / ".control_plane" / "work_queue" / "history.jsonl")
            self.assertTrue(a.exists() and b.exists() and c.exists())
            self.assertEqual(json.loads(c.read_text(encoding="utf-8").splitlines()[0])["report_id"], "x")


if __name__ == "__main__":
    unittest.main()
