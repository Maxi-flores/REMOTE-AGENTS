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


class TestPortfolioProgressAnalyzer(unittest.TestCase):
    def test_report_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".control_plane" / "portfolio").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "portfolio" / "latest.json").write_text(
                json.dumps(
                    {
                        "report_id": "p2",
                        "portfolio_health_score": 86,
                        "portfolio_readiness_score": 35,
                        "repository_statuses": [{"repository_id": "A", "health_score": 80, "readiness_score": 50}],
                    }
                ),
                encoding="utf-8",
            )
            (root / ".control_plane" / "portfolio" / "history.jsonl").write_text(
                json.dumps(
                    {
                        "report_id": "p1",
                        "portfolio_health_score": 82,
                        "portfolio_readiness_score": 20,
                        "repository_statuses": [{"repository_id": "A", "health_score": 70, "readiness_score": 40}],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (root / ".control_plane" / "portfolio_bootstrap").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "portfolio_bootstrap" / "latest.json").write_text(
                json.dumps({"report_id": "b2", "readiness_summary": {"average_readiness_estimate": 60}, "onboarding_records": [{"repository_id": "A", "readiness_estimate": 60, "onboarding_state": "discovered"}]}),
                encoding="utf-8",
            )
            (root / ".control_plane" / "portfolio_bootstrap" / "history.jsonl").write_text(
                json.dumps({"report_id": "b1", "readiness_summary": {"average_readiness_estimate": 50}, "onboarding_records": [{"repository_id": "A", "readiness_estimate": 50, "onboarding_state": "unknown"}]}) + "\n",
                encoding="utf-8",
            )
            (root / ".control_plane" / "portfolio_dependencies").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "portfolio_dependencies" / "latest.json").write_text(
                json.dumps({"report_id": "d2", "findings": [{"repository_id": "A", "severity": "high"}]}),
                encoding="utf-8",
            )
            (root / ".control_plane" / "portfolio_dependencies" / "history.jsonl").write_text(
                json.dumps({"report_id": "d1", "findings": [{"repository_id": "A", "severity": "high"}, {"repository_id": "A", "severity": "critical"}]}) + "\n",
                encoding="utf-8",
            )
            (root / ".control_plane" / "portfolio_critical_path").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "portfolio_critical_path" / "latest.json").write_text(
                json.dumps({"report_id": "c2", "recommendations": [{"recommendation_id": "r1"}], "critical_repository_scores": [{"repository_id": "A", "critical_path_score": 75}]}),
                encoding="utf-8",
            )
            (root / ".control_plane" / "portfolio_critical_path" / "history.jsonl").write_text(
                json.dumps({"report_id": "c1", "recommendations": [{"recommendation_id": "r1"}, {"recommendation_id": "r2"}], "critical_repository_scores": [{"repository_id": "A", "critical_path_score": 80}]}) + "\n",
                encoding="utf-8",
            )
            (root / ".control_plane" / "portfolio_roadmap").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "portfolio_roadmap" / "latest.json").write_text(
                json.dumps({"report_id": "r2", "roadmap_items": [{"item_id": "i1"}], "waves": [{"wave_id": "wave_1"}]}),
                encoding="utf-8",
            )
            (root / ".control_plane" / "portfolio_roadmap" / "history.jsonl").write_text(
                json.dumps({"report_id": "r1", "roadmap_items": [{"item_id": "i1"}, {"item_id": "i2"}], "waves": [{"wave_id": "wave_1"}, {"wave_id": "wave_2"}]}) + "\n",
                encoding="utf-8",
            )

            report = generate_portfolio_progress_report(base_dir=root)
            self.assertTrue(len(report["metrics"]) > 0)
            self.assertIn("portfolio_trends", report)
            metric_names = [m["metric_name"] for m in report["metrics"] if m["repository_id"] == "portfolio"]
            self.assertIn("portfolio_health_score", metric_names)


if __name__ == "__main__":
    unittest.main()

