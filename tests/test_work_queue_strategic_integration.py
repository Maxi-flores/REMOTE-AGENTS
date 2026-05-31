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


class TestWorkQueueStrategicIntegration(unittest.TestCase):
    def test_queue_candidates_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".control_plane" / "executive").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "work_queue").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "executive" / "executive_briefing.json").write_text(
                json.dumps({"overall_status": "healthy", "top_risks": [], "recommended_actions": []}), encoding="utf-8"
            )
            (root / ".control_plane" / "work_queue" / "latest.json").write_text(
                json.dumps({"queue_items": [{"queue_item_id": "q1", "title": "x", "priority": "P1", "readiness_score": 95, "effort_score": 20, "recommended_position": 1, "execution_readiness": "ready"}]}),
                encoding="utf-8",
            )
            report = generate_strategic_mission_report(base_dir=root)
            self.assertTrue(any("execute queue item" in str(c.get("title", "")).lower() for c in report["candidates"]))


if __name__ == "__main__":
    unittest.main()
