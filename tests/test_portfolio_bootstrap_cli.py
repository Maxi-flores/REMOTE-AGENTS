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

from portfolio_bootstrap.cli import main  # noqa: E402


class TestPortfolioBootstrapCli(unittest.TestCase):
    def test_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".config" / "portfolio").mkdir(parents=True, exist_ok=True)
            (root / ".config" / "portfolio" / "portfolio_registry.json").write_text(
                json.dumps(
                    {
                        "repositories": [
                            {
                                "repository_id": "A",
                                "repository_name": "A",
                                "repository_path": ".",
                                "repository_type": "agent",
                                "enabled": True,
                                "metadata": {},
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            out = io.StringIO()
            rc = main(["--print", "--export", "--export-jsonl", "--base-dir", str(root)], stdout=out)
            self.assertEqual(rc, 0)
            self.assertIn("Portfolio Bootstrap Summary", out.getvalue())
            self.assertTrue((root / ".control_plane" / "portfolio_bootstrap" / "latest.json").exists())


if __name__ == "__main__":
    unittest.main()

