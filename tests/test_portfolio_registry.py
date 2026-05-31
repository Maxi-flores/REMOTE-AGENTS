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

from portfolio_orchestration.registry import list_enabled_repositories, load_portfolio_registry  # noqa: E402


class TestPortfolioRegistry(unittest.TestCase):
    def test_load_registry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reg = root / ".config" / "portfolio"
            reg.mkdir(parents=True, exist_ok=True)
            (reg / "portfolio_registry.json").write_text(
                json.dumps(
                    {
                        "repositories": [
                            {
                                "repository_id": "R1",
                                "repository_name": "R1",
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
            repos = load_portfolio_registry(base_dir=root)
            self.assertEqual(len(repos), 1)
            enabled = list_enabled_repositories(base_dir=root)
            self.assertEqual(len(enabled), 1)


if __name__ == "__main__":
    unittest.main()

