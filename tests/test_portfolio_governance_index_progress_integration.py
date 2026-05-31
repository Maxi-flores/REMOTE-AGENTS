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

from portfolio_progress.analyzer import generate_portfolio_progress_report  # noqa: E402


class TestPortfolioGovernanceIndexProgressIntegration(unittest.TestCase):
    def test_progress_has_governance_metric(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".control_plane" / "portfolio").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "portfolio" / "latest.json").write_text(
                json.dumps({"portfolio_health_score": 80, "portfolio_readiness_score": 70, "repository_statuses": []}),
                encoding="utf-8",
            )
            (root / ".control_plane" / "portfolio_governance_index").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "portfolio_governance_index" / "latest.json").write_text(
                json.dumps({"report_id": "g2", "governance_score": 75}),
                encoding="utf-8",
            )
            (root / ".control_plane" / "portfolio_governance_index" / "history.jsonl").write_text(
                json.dumps({"report_id": "g1", "governance_score": 70}) + "\n",
                encoding="utf-8",
            )
            report = generate_portfolio_progress_report(base_dir=root)
            names = [m["metric_name"] for m in report.get("metrics", []) if m.get("repository_id") == "portfolio"]
            self.assertIn("governance_score", names)


if __name__ == "__main__":
    unittest.main()

