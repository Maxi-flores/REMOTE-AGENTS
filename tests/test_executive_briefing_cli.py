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

from control_plane.bootstrap import bootstrap_advisory_artifacts  # noqa: E402
from executive_briefing.cli import main  # noqa: E402


class TestExecutiveBriefingCli(unittest.TestCase):
    def test_print_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            bootstrap_advisory_artifacts(base)
            out = io.StringIO()
            code = main(["--print", "--from-control-plane", tmp], stdout=out)
            self.assertEqual(code, 0)
            self.assertIn("System Status:", out.getvalue())

    def test_export_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            bootstrap_advisory_artifacts(base)
            code = main(["--export", "--from-control-plane", tmp], stdout=io.StringIO())
            self.assertEqual(code, 0)
            self.assertTrue((base / ".control_plane" / "executive" / "executive_briefing.json").exists())

    def test_export_jsonl_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            bootstrap_advisory_artifacts(base)
            code = main(["--export-jsonl", "--from-control-plane", tmp], stdout=io.StringIO())
            self.assertEqual(code, 0)
            path = base / ".control_plane" / "executive" / "executive_briefings.jsonl"
            self.assertTrue(path.exists())
            self.assertTrue(isinstance(json.loads(path.read_text(encoding="utf-8").splitlines()[0]), dict))


if __name__ == "__main__":
    unittest.main()

