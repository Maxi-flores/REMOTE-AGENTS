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

from handoff_refinement.cli import main  # noqa: E402


class TestHandoffRefinementNoQueueMutation(unittest.TestCase):
    def test_queue_unmodified(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue = root / ".platform_queue"
            queue.mkdir(parents=True, exist_ok=True)
            qf = queue / "next_task.json"
            qf.write_text('{"task_id":"legacy"}', encoding="utf-8")
            before = qf.read_text(encoding="utf-8")
            handoff_dir = root / ".control_plane" / "remediation_handoffs"
            handoff_dir.mkdir(parents=True, exist_ok=True)
            (handoff_dir / "latest.json").write_text(json.dumps({"report_id": "h1", "packages": []}), encoding="utf-8")
            rc = main(["--export", "--export-jsonl", "--base-dir", str(root)])
            self.assertEqual(rc, 0)
            after = qf.read_text(encoding="utf-8")
            self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
