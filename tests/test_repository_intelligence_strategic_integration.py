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


class TestRepositoryIntelligenceStrategicIntegration(unittest.TestCase):
    def test_optional_integration_when_report_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / ".control_plane" / "executive").mkdir(parents=True, exist_ok=True)
            (base / ".control_plane" / "executive" / "executive_briefing.json").write_text(
                json.dumps({"overall_status": "healthy", "top_risks": [], "recommended_actions": []}),
                encoding="utf-8",
            )
            (base / ".control_plane" / "repository_intelligence").mkdir(parents=True, exist_ok=True)
            (base / ".control_plane" / "repository_intelligence" / "repository_intelligence_report.json").write_text(
                json.dumps(
                    {
                        "findings": [
                            {
                                "finding_id": "rf1",
                                "category": "testing",
                                "severity": "high",
                                "title": "CLI without matching CLI test",
                                "description": "desc",
                                "path_refs": ["src/foo/cli.py"],
                                "recommended_action": "Add CLI tests.",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            report = generate_strategic_mission_report(base_dir=base)
            self.assertTrue(any("CLI" in str(c.get("title", "")) for c in report["candidates"] if isinstance(c, dict)))


if __name__ == "__main__":
    unittest.main()

