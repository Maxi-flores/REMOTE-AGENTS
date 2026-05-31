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

from portfolio_bootstrap.discovery import discover_portfolio_repositories  # noqa: E402


class TestPortfolioBootstrapDiscovery(unittest.TestCase):
    def test_discovery(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".config" / "portfolio").mkdir(parents=True, exist_ok=True)
            repo = root / "repo-a"
            (repo / "docs").mkdir(parents=True, exist_ok=True)
            (repo / "src").mkdir(parents=True, exist_ok=True)
            (repo / "tests").mkdir(parents=True, exist_ok=True)
            (repo / "README.md").write_text("x", encoding="utf-8")
            (repo / ".control_plane" / "work_queue").mkdir(parents=True, exist_ok=True)
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
            found = discover_portfolio_repositories(base_dir=root)
            self.assertEqual(len(found), 1)
            self.assertTrue(found[0]["exists"])
            self.assertTrue(found[0]["structure"]["readme"])
            self.assertTrue(found[0]["artifacts"]["control_plane_root"])


if __name__ == "__main__":
    unittest.main()

