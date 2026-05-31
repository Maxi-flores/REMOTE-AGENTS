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

from governance_approval_packets.cli import main  # noqa: E402


class TestGovernanceApprovalPacketsNoQueueMutation(unittest.TestCase):
    def test_queue_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            qdir = root / ".platform_queue"
            qdir.mkdir(parents=True, exist_ok=True)
            qfile = qdir / "next_task.json"
            qfile.write_text('{"task_id":"legacy"}', encoding="utf-8")
            before = qfile.read_text(encoding="utf-8")

            (root / ".control_plane" / "governance_approval_readiness").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "governance_recovery_dossiers").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "governance_approval_readiness" / "latest.json").write_text(json.dumps({"report_id": "rr1", "records": []}), encoding="utf-8")
            (root / ".control_plane" / "governance_recovery_dossiers" / "latest.json").write_text(json.dumps({"report_id": "dr1", "dossiers": []}), encoding="utf-8")

            rc = main(["--export", "--export-jsonl", "--base-dir", str(root)])
            self.assertEqual(rc, 0)
            self.assertEqual(before, qfile.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

