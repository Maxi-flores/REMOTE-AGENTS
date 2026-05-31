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

from portfolio_governance_index.analyzer import generate_portfolio_governance_health_report  # noqa: E402


class TestPortfolioGovernanceIndexAnalyzer(unittest.TestCase):
    def test_analyzer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".control_plane" / "portfolio").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "portfolio_bootstrap").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "portfolio_onboarding_recommendations").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "portfolio_dependencies").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "portfolio_critical_path").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "portfolio_roadmap").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "portfolio_progress").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "portfolio_drift").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "portfolio" / "latest.json").write_text(json.dumps({"portfolio_health_score": 80, "portfolio_readiness_score": 60}), encoding="utf-8")
            (root / ".control_plane" / "portfolio_bootstrap" / "latest.json").write_text(json.dumps({"readiness_summary": {"average_readiness_estimate": 70}, "onboarding_records": [{"artifact_status": "none"}]}), encoding="utf-8")
            (root / ".control_plane" / "portfolio_dependencies" / "latest.json").write_text(json.dumps({"findings": [{"severity": "high"}]}), encoding="utf-8")
            (root / ".control_plane" / "portfolio_critical_path" / "latest.json").write_text(json.dumps({"recommendations": [{"priority": "P1"}]}), encoding="utf-8")
            (root / ".control_plane" / "portfolio_roadmap" / "latest.json").write_text(json.dumps({"waves": [{"items": ["a"]}, {"items": []}, {"items": []}]}), encoding="utf-8")
            (root / ".control_plane" / "portfolio_progress" / "latest.json").write_text(json.dumps({"portfolio_trends": {"trend_counts": {"improving": 1, "stable": 1, "declining": 0}}}), encoding="utf-8")
            (root / ".control_plane" / "portfolio_drift" / "latest.json").write_text(json.dumps({"summary": {"severity_counts": {"high": 0, "critical": 0, "low": 1, "medium": 0}}}), encoding="utf-8")
            report = generate_portfolio_governance_health_report(base_dir=root)
            self.assertIn("governance_score", report)
            self.assertIn("components", report)
            self.assertTrue(len(report["components"]) == 8)


if __name__ == "__main__":
    unittest.main()

