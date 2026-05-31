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

from portfolio_roadmap.planner import generate_portfolio_roadmap_report  # noqa: E402


class TestPortfolioRoadmapPlanner(unittest.TestCase):
    def test_planner_generates_waves(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".config" / "portfolio").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "portfolio_critical_path").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "portfolio_dependencies").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "portfolio").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "portfolio_onboarding_recommendations").mkdir(parents=True, exist_ok=True)
            (root / ".config" / "portfolio" / "portfolio_registry.json").write_text(
                json.dumps(
                    {
                        "repositories": [
                            {"repository_id": "Sentient-OS", "repository_name": "Sentient-OS", "repository_path": ".", "repository_type": "platform", "enabled": True, "metadata": {}},
                            {"repository_id": "TRT", "repository_name": "TRT", "repository_path": ".", "repository_type": "platform", "enabled": True, "metadata": {}},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (root / ".control_plane" / "portfolio_critical_path" / "latest.json").write_text(
                json.dumps(
                    {
                        "report_id": "cp1",
                        "recommendations": [
                            {"recommendation_id": "r1", "repository_id": "Sentient-OS", "priority": "P1", "title": "Critical path action for Sentient-OS", "recommended_action": "Do X", "expected_portfolio_impact": "I", "dependency_refs": ["TRT"]},
                            {"recommendation_id": "r2", "repository_id": "TRT", "priority": "P2", "title": "Critical path action for TRT", "recommended_action": "Do Y", "expected_portfolio_impact": "I", "dependency_refs": []},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (root / ".control_plane" / "portfolio_dependencies" / "latest.json").write_text(
                json.dumps({"dependency_graph": {"Sentient-OS": ["TRT"], "TRT": []}}), encoding="utf-8"
            )
            (root / ".control_plane" / "portfolio" / "latest.json").write_text(
                json.dumps({"repository_statuses": [{"repository_id": "Sentient-OS", "overall_status": "degraded"}, {"repository_id": "TRT", "overall_status": "healthy"}]}),
                encoding="utf-8",
            )
            (root / ".control_plane" / "portfolio_onboarding_recommendations" / "latest.json").write_text(
                json.dumps({"recommendations": [{"repository_id": "Sentient-OS", "priority": "P1"}]}), encoding="utf-8"
            )

            report = generate_portfolio_roadmap_report(base_dir=root)
            self.assertEqual(report["source_critical_path_report_id"], "cp1")
            self.assertGreaterEqual(len(report["roadmap_items"]), 2)
            self.assertEqual(report["roadmap_items"][0]["horizon"], "near_term")
            self.assertEqual(len(report["waves"]), 3)


if __name__ == "__main__":
    unittest.main()
