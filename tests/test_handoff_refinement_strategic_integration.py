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


class TestHandoffRefinementStrategicIntegration(unittest.TestCase):
    def test_prefers_refined_packages_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".control_plane" / "executive").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "handoff_refinements").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "remediation_handoffs").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "executive" / "executive_briefing.json").write_text(
                json.dumps({"overall_status": "healthy", "top_risks": [], "recommended_actions": []}),
                encoding="utf-8",
            )
            (root / ".control_plane" / "handoff_refinements" / "latest.json").write_text(
                json.dumps({"refined_packages": [{"refined_package_id": "r1", "title": "mission_engine cli", "metadata": {"repository": "REMOTE-AGENTS"}}]}),
                encoding="utf-8",
            )
            (root / ".control_plane" / "remediation_handoffs" / "latest.json").write_text(
                json.dumps({"packages": [{"source_batch_id": "b1", "title": "broad package"}]}),
                encoding="utf-8",
            )
            report = generate_strategic_mission_report(base_dir=root)
            titles = [str(c.get("title", "")).lower() for c in report["candidates"]]
            self.assertTrue(any("refined package" in t for t in titles))


if __name__ == "__main__":
    unittest.main()
