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


class TestPortfolioAggregator(unittest.TestCase):
    def test_generate_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reg_dir = root / ".config" / "portfolio"
            reg_dir.mkdir(parents=True, exist_ok=True)
            (reg_dir / "portfolio_registry.json").write_text(
                json.dumps(
                    {
                        "repositories": [
                            {
                                "repository_id": "REMOTE-AGENTS",
                                "repository_name": "REMOTE-AGENTS",
                                "repository_path": ".",
                                "repository_type": "agent",
                                "enabled": True,
                                "metadata": {},
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            cp = root / ".control_plane"
            (cp / "repository_intelligence").mkdir(parents=True, exist_ok=True)
            (cp / "remediation_plans").mkdir(parents=True, exist_ok=True)
            (cp / "work_queue").mkdir(parents=True, exist_ok=True)
            (cp / "execution_dossiers").mkdir(parents=True, exist_ok=True)
            (cp / "repository_intelligence" / "repository_intelligence_report.json").write_text(
                json.dumps({"findings": [{"path_refs": ["REMOTE-AGENTS/src/x.py"], "severity": "high"}]}),
                encoding="utf-8",
            )
            (cp / "remediation_plans" / "remediation_plan_report.json").write_text(
                json.dumps({"items": [{"repository_name": "REMOTE-AGENTS"}]}),
                encoding="utf-8",
            )
            (cp / "work_queue" / "latest.json").write_text(
                json.dumps({"queue_items": [{"readiness_score": 80, "metadata": {"repository_name": "REMOTE-AGENTS"}}]}),
                encoding="utf-8",
            )
            (cp / "execution_dossiers" / "latest.json").write_text(
                json.dumps(
                    {
                        "dossiers": [
                            {
                                "execution_readiness_score": 85,
                                "execution_risk": "low",
                                "metadata": {"repository_name": "REMOTE-AGENTS"},
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            report = generate_portfolio_report(base_dir=root)
            self.assertEqual(len(report["repositories"]), 1)
            self.assertEqual(len(report["repository_statuses"]), 1)
            self.assertIn("portfolio_health_score", report)


if __name__ == "__main__":
    unittest.main()

