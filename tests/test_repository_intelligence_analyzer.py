from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from repository_intelligence.analyzer import analyze_repository_intelligence  # noqa: E402


class TestRepositoryIntelligenceAnalyzer(unittest.TestCase):
    def test_analyzer_generates_deterministic_findings(self) -> None:
        inventory = {
            "inventory_id": "i1",
            "generated_utc": "2026-01-01T00:00:00Z",
            "root_path": "C:/repo",
            "source_directories": ["src/foo", "src/bar"],
            "test_files": ["tests/test_foo.py"],
            "documentation_files": ["docs/foo.md"],
            "config_files": ["config/a.json"],
            "package_files": ["README.md"],
            "runtime_entrypoints": ["src/foo/cli.py", "src/orchestrator/platform_engine.py"],
            "advisory_only": True,
            "metadata": {},
        }
        report = analyze_repository_intelligence(inventory, repository_name="repo")
        self.assertIn(report["overall_status"], {"warning", "degraded", "critical", "healthy"})
        self.assertTrue(isinstance(report["findings"], list))
        self.assertGreaterEqual(len(report["findings"]), 1)
        titles = [f.get("title", "") for f in report["findings"] if isinstance(f, dict)]
        self.assertTrue(any("CLI" in t or "Source module" in t for t in titles))


if __name__ == "__main__":
    unittest.main()

