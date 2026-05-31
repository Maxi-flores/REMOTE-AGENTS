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

from portfolio_dependencies.registry import load_dependency_registry  # noqa: E402


class TestPortfolioDependenciesRegistry(unittest.TestCase):
    def test_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".config" / "portfolio").mkdir(parents=True, exist_ok=True)
            (root / ".config" / "portfolio" / "dependencies.json").write_text(
                json.dumps({"repositories": [{"repository_id": "A", "depends_on": ["B"], "metadata": {}}]}),
                encoding="utf-8",
            )
            records = load_dependency_registry(base_dir=root)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["depends_on"], ["B"])


if __name__ == "__main__":
    unittest.main()

