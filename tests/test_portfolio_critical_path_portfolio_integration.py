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

from portfolio_orchestration.aggregator import generate_portfolio_report  # noqa: E402


class TestPortfolioCriticalPathPortfolioIntegration(unittest.TestCase):
    def test_portfolio_reads_pcpi_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".config" / "portfolio").mkdir(parents=True, exist_ok=True)
            (root / ".config" / "portfolio" / "portfolio_registry.json").write_text(
                json.dumps({"repositories": [{"repository_id": "A", "repository_name": "A", "repository_path": ".", "repository_type": "agent", "enabled": True, "metadata": {}}]}),
                encoding="utf-8",
            )
            (root / ".control_plane" / "portfolio_critical_path").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "portfolio_critical_path" / "latest.json").write_text(
                json.dumps({"portfolio_leverage_summary": {"recommendation_count": 3}}),
                encoding="utf-8",
            )
            report = generate_portfolio_report(base_dir=root)
            self.assertIn("critical_path_summary", report["metadata"])
            self.assertTrue(any("critical path summary" in str(f.get("title", "")).lower() for f in report["findings"]))


if __name__ == "__main__":
    unittest.main()

