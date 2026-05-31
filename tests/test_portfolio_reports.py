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

from portfolio_orchestration.reports import (  # noqa: E402
    append_portfolio_report_jsonl,
    write_portfolio_report,
    write_timestamped_portfolio_report,
)


class TestPortfolioReports(unittest.TestCase):
    def test_write_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = {"report_id": "p1"}
            latest = write_portfolio_report(report, path=root / ".control_plane" / "portfolio" / "latest.json")
            self.assertTrue(latest.exists())
            stamped = write_timestamped_portfolio_report(report, directory=root / ".control_plane" / "portfolio")
            self.assertTrue(stamped.exists())
            hist = append_portfolio_report_jsonl(report, path=root / ".control_plane" / "portfolio" / "history.jsonl")
            self.assertTrue(hist.exists())
            line = hist.read_text(encoding="utf-8").strip()
            self.assertEqual(json.loads(line)["report_id"], "p1")


if __name__ == "__main__":
    unittest.main()

