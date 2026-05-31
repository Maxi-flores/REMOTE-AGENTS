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


class TestPortfolioExecutiveIntegration(unittest.TestCase):
    def test_portfolio_findings_included(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdir = root / ".control_plane" / "portfolio"
            pdir.mkdir(parents=True, exist_ok=True)
            (pdir / "latest.json").write_text(
                json.dumps(
                    {
                        "portfolio_health_score": 60,
                        "portfolio_readiness_score": 55,
                        "repository_statuses": [{"repository_id": "R1"}],
                        "findings": [{"severity": "high"}],
                    }
                ),
                encoding="utf-8",
            )
            prev = Path.cwd()
            try:
                import os

                os.chdir(root)
                res = analyze_artifacts()
            finally:
                os.chdir(prev)
            self.assertTrue(any("Portfolio" in str(f.get("title", "")) for f in res["findings"]))


if __name__ == "__main__":
    unittest.main()

