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


class TestPortfolioDependenciesStrategicIntegration(unittest.TestCase):
    def test_dependency_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".control_plane" / "executive").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "executive" / "executive_briefing.json").write_text(
                json.dumps({"overall_status": "healthy", "top_risks": [], "recommended_actions": []}),
                encoding="utf-8",
            )
            (root / ".control_plane" / "portfolio_dependencies").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "portfolio_dependencies" / "latest.json").write_text(
                json.dumps(
                    {
                        "findings": [
                            {
                                "finding_id": "f1",
                                "severity": "high",
                                "repository_id": "TRT",
                                "recommended_action": "Resolve dependency blocker",
                                "title": "TRT blocked by Sentient-OS",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            report = generate_strategic_mission_report(base_dir=root)
            self.assertTrue(any("Dependency risk" in str(c.get("title", "")) for c in report["candidates"]))


if __name__ == "__main__":
    unittest.main()

