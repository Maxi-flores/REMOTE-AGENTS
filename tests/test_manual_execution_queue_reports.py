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

from manual_execution_queue.reports import (  # noqa: E402
    append_manual_execution_queue_report_jsonl,
    write_manual_execution_queue_report,
)


class TestManualExecutionQueueReports(unittest.TestCase):
    def test_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = write_manual_execution_queue_report(
                {"report_id": "r1"},
                path=Path(tmp) / ".control_plane" / "manual_execution_queue" / "latest.json",
            )
            self.assertEqual(json.loads(p.read_text(encoding="utf-8"))["report_id"], "r1")

    def test_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = append_manual_execution_queue_report_jsonl(
                {"report_id": "r1"},
                path=Path(tmp) / ".control_plane" / "manual_execution_queue" / "history.jsonl",
            )
            self.assertEqual(len(p.read_text(encoding="utf-8").splitlines()), 1)


if __name__ == "__main__":
    unittest.main()

