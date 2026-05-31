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

from governance_recovery_dossiers.cli import main  # noqa: E402


class TestGovernanceRecoveryDossiersNoQueueMutation(unittest.TestCase):
    def test_queue_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            queue = root / ".platform_queue"
            queue.mkdir(parents=True, exist_ok=True)
            qfile = queue / "next_task.json"
            qfile.write_text('{"task_id":"legacy"}', encoding="utf-8")
            before = qfile.read_text(encoding="utf-8")

            recovery_dir = root / ".control_plane" / "governance_recovery"
            recovery_dir.mkdir(parents=True, exist_ok=True)
            (recovery_dir / "latest.json").write_text(
                json.dumps({"report_id": "gr1", "actions": [], "waves": []}),
                encoding="utf-8",
            )

            rc = main(["--export", "--export-jsonl", "--base-dir", str(root)])
            self.assertEqual(rc, 0)
            self.assertEqual(before, qfile.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

