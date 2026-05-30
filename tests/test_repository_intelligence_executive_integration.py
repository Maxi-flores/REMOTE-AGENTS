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

from executive_briefing.analyzer import analyze_artifacts  # noqa: E402


class TestRepositoryIntelligenceExecutiveIntegration(unittest.TestCase):
    def test_optional_integration_when_report_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
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
                                "recommended_action": "Add CLI tests.",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            cwd = Path.cwd()
            try:
                __import__("os").chdir(base)
                result = analyze_artifacts()
            finally:
                __import__("os").chdir(cwd)
            self.assertTrue(any(f.get("category") == "repository" for f in result["findings"] if isinstance(f, dict)))


if __name__ == "__main__":
    unittest.main()

