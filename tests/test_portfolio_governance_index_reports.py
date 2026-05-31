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

from portfolio_governance_index.reports import append_portfolio_governance_health_report_jsonl, write_portfolio_governance_health_report  # noqa: E402


class TestPortfolioGovernanceIndexReports(unittest.TestCase):
    def test_write_and_append(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = write_portfolio_governance_health_report({"report_id": "g1"}, path=root / ".control_plane" / "portfolio_governance_index" / "latest.json")
            self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["report_id"], "g1")
            out2 = append_portfolio_governance_health_report_jsonl({"report_id": "g2"}, path=root / ".control_plane" / "portfolio_governance_index" / "history.jsonl")
            self.assertEqual(len(out2.read_text(encoding="utf-8").splitlines()), 1)


if __name__ == "__main__":
    unittest.main()

