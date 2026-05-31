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

from execution_dossier.cli import main  # noqa: E402


class TestExecutionDossierNoQueueMutation(unittest.TestCase):
    def test_platform_queue_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pq = root / ".platform_queue"
            pq.mkdir(parents=True, exist_ok=True)
            qf = pq / "next_task.json"
            qf.write_text('{"task_id":"legacy"}', encoding="utf-8")
            before = qf.read_text(encoding="utf-8")
            wq = root / ".control_plane" / "work_queue"
            wq.mkdir(parents=True, exist_ok=True)
            (wq / "latest.json").write_text(json.dumps({"report_id": "w1", "queue_items": []}), encoding="utf-8")
            rc = main(["--export", "--export-jsonl", "--base-dir", str(root)])
            self.assertEqual(rc, 0)
            self.assertEqual(before, qf.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
