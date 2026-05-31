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

from work_queue_manager.cli import main  # noqa: E402


class TestWorkQueueNoQueueMutation(unittest.TestCase):
    def test_no_platform_queue_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            q = root / ".platform_queue"
            q.mkdir(parents=True, exist_ok=True)
            f = q / "next_task.json"
            f.write_text('{"task_id":"legacy"}', encoding="utf-8")
            before = f.read_text(encoding="utf-8")
            d = root / ".control_plane" / "handoff_refinements"
            d.mkdir(parents=True, exist_ok=True)
            (d / "latest.json").write_text(json.dumps({"report_id": "r1", "refined_packages": []}), encoding="utf-8")
            rc = main(["--export", "--export-jsonl", "--base-dir", str(root)])
            self.assertEqual(rc, 0)
            self.assertEqual(before, f.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
