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

from strategic_missions.generator import generate_strategic_mission_report  # noqa: E402


class TestPortfolioRoadmapStrategicIntegration(unittest.TestCase):
    def test_roadmap_candidates_are_generated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".control_plane" / "portfolio_roadmap").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "portfolio_roadmap" / "latest.json").write_text(
                json.dumps(
                    {
                        "roadmap_items": [
                            {
                                "source_recommendation_id": "r1",
                                "repository_id": "Sentient-OS",
                                "priority": "P1",
                                "title": "Critical path action",
                                "objective": "Do thing",
                                "wave": "wave_1",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            report = generate_strategic_mission_report(
                briefing={"overall_status": "healthy", "top_risks": [], "recommended_actions": []},
                base_dir=root,
            )
            titles = [str(c.get("title") or "") for c in report["candidates"] if isinstance(c, dict)]
            self.assertTrue(any("Roadmap wave action" in title for title in titles))


if __name__ == "__main__":
    unittest.main()
