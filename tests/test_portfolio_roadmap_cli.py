from __future__ import annotations

import io
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

from portfolio_roadmap.cli import main  # noqa: E402


def _seed(root: Path) -> None:
    (root / ".config" / "portfolio").mkdir(parents=True, exist_ok=True)
    (root / ".control_plane" / "portfolio_critical_path").mkdir(parents=True, exist_ok=True)
    (root / ".control_plane" / "portfolio_dependencies").mkdir(parents=True, exist_ok=True)
    (root / ".control_plane" / "portfolio").mkdir(parents=True, exist_ok=True)
    (root / ".control_plane" / "portfolio_onboarding_recommendations").mkdir(parents=True, exist_ok=True)
    (root / ".config" / "portfolio" / "portfolio_registry.json").write_text(
        json.dumps({"repositories": [{"repository_id": "Sentient-OS", "repository_name": "Sentient-OS", "repository_path": ".", "repository_type": "platform", "enabled": True, "metadata": {}}]}),
        encoding="utf-8",
    )
    (root / ".control_plane" / "portfolio_critical_path" / "latest.json").write_text(
        json.dumps({"report_id": "cp1", "recommendations": [{"recommendation_id": "r1", "repository_id": "Sentient-OS", "priority": "P1", "title": "Critical path action", "recommended_action": "Do X", "expected_portfolio_impact": "I", "dependency_refs": []}]}),
        encoding="utf-8",
    )
    (root / ".control_plane" / "portfolio_dependencies" / "latest.json").write_text(json.dumps({"dependency_graph": {"Sentient-OS": []}}), encoding="utf-8")
    (root / ".control_plane" / "portfolio" / "latest.json").write_text(json.dumps({"repository_statuses": []}), encoding="utf-8")
    (root / ".control_plane" / "portfolio_onboarding_recommendations" / "latest.json").write_text(json.dumps({"recommendations": []}), encoding="utf-8")


class TestPortfolioRoadmapCLI(unittest.TestCase):
    def test_print(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed(root)
            buffer = io.StringIO()
            code = main(["--print", "--base-dir", str(root)], stdout=buffer)
            self.assertEqual(code, 0)
            self.assertIn("Portfolio Strategic Roadmap", buffer.getvalue())

    def test_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _seed(root)
            code = main(["--export", "--export-jsonl", "--base-dir", str(root)])
            self.assertEqual(code, 0)
            self.assertTrue((root / ".control_plane" / "portfolio_roadmap" / "latest.json").exists())
            self.assertTrue((root / ".control_plane" / "portfolio_roadmap" / "history.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
