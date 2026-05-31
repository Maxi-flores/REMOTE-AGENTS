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

from portfolio_critical_path.analyzer import generate_portfolio_critical_path_report  # noqa: E402


class TestPortfolioCriticalPathAnalyzer(unittest.TestCase):
    def test_analyzer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".config" / "portfolio").mkdir(parents=True, exist_ok=True)
            (root / ".config" / "portfolio" / "portfolio_registry.json").write_text(
                json.dumps(
                    {
                        "repositories": [
                            {"repository_id": "A", "repository_name": "A", "repository_path": ".", "repository_type": "agent", "enabled": True, "metadata": {}},
                            {"repository_id": "B", "repository_name": "B", "repository_path": ".", "repository_type": "agent", "enabled": True, "metadata": {}},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (root / ".control_plane" / "portfolio_dependencies").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "portfolio_dependencies" / "latest.json").write_text(
                json.dumps(
                    {
                        "dependency_graph": {"A": ["B"], "B": []},
                        "dependency_chains": [["A", "B"]],
                        "findings": [{"repository_id": "A", "severity": "high"}],
                    }
                ),
                encoding="utf-8",
            )
            (root / ".control_plane" / "portfolio").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "portfolio" / "latest.json").write_text(
                json.dumps({"repository_statuses": [{"repository_id": "A", "readiness_score": 20}, {"repository_id": "B", "readiness_score": 90}]}),
                encoding="utf-8",
            )
            (root / ".control_plane" / "portfolio_onboarding_recommendations").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "portfolio_onboarding_recommendations" / "latest.json").write_text(
                json.dumps({"recommendations": [{"repository_id": "A", "priority": "P1"}]}),
                encoding="utf-8",
            )
            report = generate_portfolio_critical_path_report(base_dir=root)
            self.assertGreaterEqual(len(report["critical_repository_scores"]), 2)
            self.assertGreaterEqual(len(report["recommendations"]), 2)


if __name__ == "__main__":
    unittest.main()

