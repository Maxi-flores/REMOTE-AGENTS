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

from portfolio_bootstrap.onboarding import generate_portfolio_bootstrap_report  # noqa: E402


class TestPortfolioBootstrapOnboarding(unittest.TestCase):
    def test_onboarding_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".config" / "portfolio").mkdir(parents=True, exist_ok=True)
            repo = root / "repo-a"
            (repo / "src").mkdir(parents=True, exist_ok=True)
            (repo / "README.md").write_text("x", encoding="utf-8")
            (root / ".config" / "portfolio" / "portfolio_registry.json").write_text(
                json.dumps(
                    {
                        "repositories": [
                            {
                                "repository_id": "A",
                                "repository_name": "A",
                                "repository_path": "repo-a",
                                "repository_type": "agent",
                                "enabled": True,
                                "metadata": {},
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            report = generate_portfolio_bootstrap_report(base_dir=root)
            self.assertEqual(len(report["onboarding_records"]), 1)
            record = report["onboarding_records"][0]
            self.assertIn(record["artifact_status"], {"none", "partial", "complete", "unknown"})
            self.assertGreaterEqual(record["readiness_estimate"], 0)
            self.assertLessEqual(record["readiness_estimate"], 100)


if __name__ == "__main__":
    unittest.main()

