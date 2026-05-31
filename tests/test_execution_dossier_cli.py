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

from execution_dossier.cli import main  # noqa: E402


class TestExecutionDossierCli(unittest.TestCase):
    def test_cli_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            qd = root / ".control_plane" / "work_queue"
            qd.mkdir(parents=True, exist_ok=True)
            (qd / "latest.json").write_text(json.dumps({"report_id": "w1", "queue_items": []}), encoding="utf-8")
            out = io.StringIO()
            rc = main(["--print", "--export", "--export-jsonl", "--base-dir", str(root)], stdout=out)
            self.assertEqual(rc, 0)
            self.assertIn("Execution Dossiers", out.getvalue())
            self.assertTrue((root / ".control_plane" / "execution_dossiers" / "latest.json").exists())


if __name__ == "__main__":
    unittest.main()
