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

from governance_decisions.cli import main  # noqa: E402


class TestGovernanceDecisionsNoQueueMutation(unittest.TestCase):
    def test_queue_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            qdir = root / ".platform_queue"
            qdir.mkdir(parents=True, exist_ok=True)
            qfile = qdir / "next_task.json"
            qfile.write_text('{"task_id":"legacy"}', encoding="utf-8")
            before = qfile.read_text(encoding="utf-8")

            pdir = root / ".control_plane" / "governance_approval_packets"
            pdir.mkdir(parents=True, exist_ok=True)
            (pdir / "latest.json").write_text(
                json.dumps({"report_id": "pr1", "packets": [{"packet_id": "p1", "source_dossier_id": "d1"}]}),
                encoding="utf-8",
            )
            rc = main(
                [
                    "--record-decision",
                    "--base-dir",
                    str(root),
                    "--packet-id",
                    "p1",
                    "--decision",
                    "defer",
                    "--reviewer",
                    "Max",
                    "--notes",
                    "Later",
                ]
            )
            self.assertEqual(rc, 0)
            self.assertEqual(before, qfile.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

