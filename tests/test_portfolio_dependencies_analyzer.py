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

from portfolio_dependencies.analyzer import generate_dependency_graph_report  # noqa: E402


class TestPortfolioDependenciesAnalyzer(unittest.TestCase):
    def test_detects_blockers_and_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".config" / "portfolio").mkdir(parents=True, exist_ok=True)
            (root / ".config" / "portfolio" / "portfolio_registry.json").write_text(
                json.dumps(
                    {
                        "repositories": [
                            {"repository_id": "TRT", "repository_name": "TRT", "repository_path": ".", "repository_type": "tooling", "enabled": True, "metadata": {}},
                            {"repository_id": "Sentient-OS", "repository_name": "Sentient OS", "repository_path": ".", "repository_type": "platform", "enabled": True, "metadata": {}},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (root / ".config" / "portfolio" / "dependencies.json").write_text(
                json.dumps(
                    {
                        "repositories": [
                            {"repository_id": "TRT", "depends_on": ["Sentient-OS", "Unknown-Repo"], "metadata": {}},
                            {"repository_id": "Sentient-OS", "depends_on": [], "metadata": {}},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (root / ".control_plane" / "portfolio_bootstrap").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "portfolio_bootstrap" / "latest.json").write_text(
                json.dumps({"onboarding_records": [{"repository_id": "Sentient-OS", "readiness_estimate": 20}]}),
                encoding="utf-8",
            )
            report = generate_dependency_graph_report(base_dir=root)
            cats = {f["category"] for f in report["findings"] if isinstance(f, dict)}
            self.assertIn("dependency_unknown", cats)
            self.assertIn("dependency_blocked", cats)


if __name__ == "__main__":
    unittest.main()

