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

from portfolio_roadmap.reports import append_portfolio_roadmap_report_jsonl, write_portfolio_roadmap_report  # noqa: E402


class TestPortfolioRoadmapReports(unittest.TestCase):
    def test_report_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = {"report_id": "r1", "advisory_only": True}
            out = write_portfolio_roadmap_report(payload, path=root / ".control_plane" / "portfolio_roadmap" / "latest.json")
            self.assertTrue(out.exists())
            parsed = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(parsed["report_id"], "r1")

    def test_jsonl_append(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = append_portfolio_roadmap_report_jsonl({"report_id": "r2"}, path=root / ".control_plane" / "portfolio_roadmap" / "history.jsonl")
            lines = out.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 1)
            self.assertEqual(json.loads(lines[0])["report_id"], "r2")


if __name__ == "__main__":
    unittest.main()

