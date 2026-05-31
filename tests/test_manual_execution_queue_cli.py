from __future__ import annotations

import io
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

from manual_execution_queue.cli import main  # noqa: E402


class TestManualExecutionQueueCLI(unittest.TestCase):
    def _seed(self, root: Path) -> None:
        (root / ".control_plane" / "governance_decisions").mkdir(parents=True, exist_ok=True)
        (root / ".control_plane" / "governance_approval_packets").mkdir(parents=True, exist_ok=True)
        (root / ".control_plane" / "governance_decisions" / "latest.json").write_text(
            json.dumps({"report_id": "dr1", "decisions": []}),
            encoding="utf-8",
        )
        (root / ".control_plane" / "governance_approval_packets" / "latest.json").write_text(
            json.dumps({"report_id": "pr1", "packets": []}),
            encoding="utf-8",
        )

    def test_print(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._seed(root)
            out = io.StringIO()
            rc = main(["--print", "--base-dir", str(root)], stdout=out)
            self.assertEqual(rc, 0)
            self.assertIn("Manual Execution Handoff Queue", out.getvalue())

    def test_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._seed(root)
            rc = main(["--export", "--export-jsonl", "--base-dir", str(root)])
            self.assertEqual(rc, 0)
            self.assertTrue((root / ".control_plane" / "manual_execution_queue" / "latest.json").exists())
            self.assertTrue((root / ".control_plane" / "manual_execution_queue" / "history.jsonl").exists())


if __name__ == "__main__":
    unittest.main()

