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


class TestRepositoryIntelligenceNoQueueMutation(unittest.TestCase):
    def test_no_queue_mutation(self) -> None:
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

            queue = base / ".platform_queue" / "next_task.json"
            queue.parent.mkdir(parents=True, exist_ok=True)
            queue.write_text('{"instruction":"existing"}\n', encoding="utf-8")
            before = queue.read_text(encoding="utf-8")
            code = main(["--export", "--base-dir", tmp], stdout=io.StringIO())
            self.assertEqual(code, 0)
            after = queue.read_text(encoding="utf-8")
            self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()

