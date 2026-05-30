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

from repository_intelligence.cli import main  # noqa: E402


class TestRepositoryIntelligenceCli(unittest.TestCase):
    def test_cli_print_export_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "src" / "alpha").mkdir(parents=True)
            (base / "src" / "alpha" / "cli.py").write_text("print('x')", encoding="utf-8")
            (base / "tests").mkdir()
            (base / "tests" / "test_alpha.py").write_text("x=1", encoding="utf-8")
            (base / "docs").mkdir()
            (base / "docs" / "alpha.md").write_text("# x", encoding="utf-8")
            (base / "config").mkdir()
            (base / "config" / "a.json").write_text("{}", encoding="utf-8")
            (base / "README.md").write_text("# r", encoding="utf-8")

            out = io.StringIO()
            code = main(["--print", "--base-dir", tmp], stdout=out)
            self.assertEqual(code, 0)
            payload = json.loads(out.getvalue())
            self.assertIn("report_id", payload)

            code = main(["--export", "--export-jsonl", "--base-dir", tmp], stdout=io.StringIO())
            self.assertEqual(code, 0)
            self.assertTrue((base / ".control_plane" / "repository_intelligence" / "repository_intelligence_report.json").exists())
            self.assertTrue((base / ".control_plane" / "repository_intelligence" / "repository_intelligence_reports.jsonl").exists())


if __name__ == "__main__":
    unittest.main()

