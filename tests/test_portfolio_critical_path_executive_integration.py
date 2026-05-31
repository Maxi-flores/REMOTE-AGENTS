from __future__ import annotations

import json
import os
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


class TestPortfolioCriticalPathExecutiveIntegration(unittest.TestCase):
    def test_executive_reads_pcpi(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            d = root / ".control_plane" / "portfolio_critical_path"
            d.mkdir(parents=True, exist_ok=True)
            (d / "latest.json").write_text(
                json.dumps({"recommendations": [{"priority": "P1"}, {"priority": "P3"}]}),
                encoding="utf-8",
            )
            prev = Path.cwd()
            try:
                os.chdir(root)
                result = analyze_artifacts()
            finally:
                os.chdir(prev)
            self.assertTrue(any("critical path actions" in str(f.get("title", "")).lower() for f in result["findings"]))


if __name__ == "__main__":
    unittest.main()

