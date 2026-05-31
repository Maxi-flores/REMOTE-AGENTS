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

from portfolio_progress.reports import append_portfolio_progress_report_jsonl, write_portfolio_progress_report  # noqa: E402


class TestPortfolioProgressReports(unittest.TestCase):
    def test_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = write_portfolio_progress_report({"report_id": "x"}, path=root / ".control_plane" / "portfolio_progress" / "latest.json")
            self.assertTrue(out.exists())
            self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["report_id"], "x")

    def test_append(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = append_portfolio_progress_report_jsonl({"report_id": "y"}, path=root / ".control_plane" / "portfolio_progress" / "history.jsonl")
            self.assertEqual(len(out.read_text(encoding="utf-8").splitlines()), 1)


if __name__ == "__main__":
    unittest.main()

