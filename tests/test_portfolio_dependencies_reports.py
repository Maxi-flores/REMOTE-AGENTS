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

from portfolio_dependencies.reports import (  # noqa: E402
    append_dependency_graph_report_jsonl,
    write_dependency_graph_report,
    write_timestamped_dependency_graph_report,
)


class TestPortfolioDependenciesReports(unittest.TestCase):
    def test_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = {"report_id": "d1"}
            latest = write_dependency_graph_report(report, path=root / ".control_plane" / "portfolio_dependencies" / "latest.json")
            self.assertTrue(latest.exists())
            stamped = write_timestamped_dependency_graph_report(report, directory=root / ".control_plane" / "portfolio_dependencies")
            self.assertTrue(stamped.exists())
            hist = append_dependency_graph_report_jsonl(report, path=root / ".control_plane" / "portfolio_dependencies" / "history.jsonl")
            self.assertEqual(json.loads(hist.read_text(encoding="utf-8").strip())["report_id"], "d1")


if __name__ == "__main__":
    unittest.main()

