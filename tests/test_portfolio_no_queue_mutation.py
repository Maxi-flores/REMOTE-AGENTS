from __future__ import annotations

import hashlib
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

from portfolio_orchestration.aggregator import generate_portfolio_report  # noqa: E402


class TestPortfolioNoQueueMutation(unittest.TestCase):
    def test_queue_file_not_mutated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".config" / "portfolio").mkdir(parents=True, exist_ok=True)
            (root / ".config" / "portfolio" / "portfolio_registry.json").write_text(
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
            q = root / ".platform_queue"
            q.mkdir(parents=True, exist_ok=True)
            queue_file = q / "next_task.json"
            queue_file.write_text('{"instruction":"keep me"}', encoding="utf-8")
            before = hashlib.sha256(queue_file.read_bytes()).hexdigest()
            generate_portfolio_report(base_dir=root)
            after = hashlib.sha256(queue_file.read_bytes()).hexdigest()
            self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()

