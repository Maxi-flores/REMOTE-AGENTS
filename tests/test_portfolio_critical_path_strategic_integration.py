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


class TestPortfolioCriticalPathStrategicIntegration(unittest.TestCase):
    def test_strategic_reads_pcpi(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".control_plane" / "executive").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "executive" / "executive_briefing.json").write_text(
                json.dumps({"overall_status": "healthy", "top_risks": [], "recommended_actions": []}),
                encoding="utf-8",
            )
            (root / ".control_plane" / "portfolio_critical_path").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "portfolio_critical_path" / "latest.json").write_text(
                json.dumps({"recommendations": [{"recommendation_id": "r1", "repository_id": "Sentient-OS", "priority": "P1", "title": "Critical path action", "recommended_action": "Do thing"}]}),
                encoding="utf-8",
            )
            report = generate_strategic_mission_report(base_dir=root)
            self.assertTrue(any("Critical path:" in str(c.get("title", "")) for c in report["candidates"]))


if __name__ == "__main__":
    unittest.main()

