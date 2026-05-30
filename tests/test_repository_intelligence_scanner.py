from __future__ import annotations

import tempfile
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from repository_intelligence.scanner import build_repository_inventory  # noqa: E402


class TestRepositoryIntelligenceScanner(unittest.TestCase):
    def test_scanner_detects_expected_and_ignores_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "src" / "alpha").mkdir(parents=True)
            (base / "src" / "alpha" / "cli.py").write_text("print('x')", encoding="utf-8")
            (base / "tests").mkdir()
            (base / "tests" / "test_alpha.py").write_text("x=1", encoding="utf-8")
            (base / "docs").mkdir()
            (base / "docs" / "alpha.md").write_text("# alpha", encoding="utf-8")
            (base / "config").mkdir()
            (base / "config" / "a.json").write_text("{}", encoding="utf-8")
            (base / "README.md").write_text("# r", encoding="utf-8")
            (base / "package.json").write_text("{}", encoding="utf-8")
            (base / "requirements.txt").write_text("", encoding="utf-8")
            (base / "node_modules").mkdir()
            (base / "node_modules" / "ignored.txt").write_text("x", encoding="utf-8")
            (base / ".git").mkdir()
            (base / ".git" / "ignored.txt").write_text("x", encoding="utf-8")
            (base / "__pycache__").mkdir()
            (base / "__pycache__" / "ignored.pyc").write_text("x", encoding="utf-8")
            (base / ".control_plane").mkdir()
            (base / ".control_plane" / "ignored.json").write_text("{}", encoding="utf-8")

            inv = build_repository_inventory(base)
            self.assertIn("src/alpha", inv["source_directories"])
            self.assertIn("tests/test_alpha.py", inv["test_files"])
            self.assertIn("docs/alpha.md", inv["documentation_files"])
            self.assertIn("config/a.json", inv["config_files"])
            self.assertIn("src/alpha/cli.py", inv["runtime_entrypoints"])
            all_paths = " ".join(inv["test_files"] + inv["documentation_files"] + inv["config_files"] + inv["runtime_entrypoints"])
            self.assertNotIn("node_modules", all_paths)
            self.assertNotIn(".git", all_paths)
            self.assertNotIn("__pycache__", all_paths)
            self.assertNotIn(".control_plane", all_paths)


if __name__ == "__main__":
    unittest.main()

