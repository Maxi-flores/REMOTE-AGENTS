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


class TestPortfolioRoadmapPortfolioIntegration(unittest.TestCase):
    def test_portfolio_metadata_includes_roadmap_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".config" / "portfolio").mkdir(parents=True, exist_ok=True)
            (root / ".config" / "portfolio" / "portfolio_registry.json").write_text(
                json.dumps({"repositories": [{"repository_id": "A", "repository_name": "A", "repository_path": ".", "repository_type": "platform", "enabled": True, "metadata": {}}]}),
                encoding="utf-8",
            )
            (root / ".control_plane" / "portfolio_roadmap").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "portfolio_roadmap" / "latest.json").write_text(
                json.dumps({"report_id": "rr1", "roadmap_items": [{"item_id": "i1"}], "waves": [{"wave_id": "wave_1"}]}),
                encoding="utf-8",
            )
            report = generate_portfolio_report(base_dir=root)
            summary = report.get("metadata", {}).get("roadmap_summary", {})
            self.assertEqual(summary.get("roadmap_item_count"), 1)


if __name__ == "__main__":
    unittest.main()
