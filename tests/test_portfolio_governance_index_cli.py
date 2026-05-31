from __future__ import annotations

import io
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

from portfolio_governance_index.cli import main  # noqa: E402


class TestPortfolioGovernanceIndexCLI(unittest.TestCase):
    def test_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".control_plane" / "portfolio").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "portfolio" / "latest.json").write_text(json.dumps({"portfolio_health_score": 80, "portfolio_readiness_score": 80}), encoding="utf-8")
            buf = io.StringIO()
            self.assertEqual(main(["--print", "--base-dir", str(root)], stdout=buf), 0)
            self.assertIn("Portfolio Governance Health Index", buf.getvalue())
            self.assertEqual(main(["--export", "--export-jsonl", "--base-dir", str(root)]), 0)
            self.assertTrue((root / ".control_plane" / "portfolio_governance_index" / "latest.json").exists())


if __name__ == "__main__":
    unittest.main()

