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

from portfolio_governance_index.analyzer import generate_portfolio_governance_health_report  # noqa: E402


class TestPortfolioGovernanceIndexNoQueueMutation(unittest.TestCase):
    def test_no_queue_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".control_plane" / "portfolio").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "portfolio" / "latest.json").write_text(
                json.dumps({"portfolio_health_score": 80, "portfolio_readiness_score": 70}),
                encoding="utf-8",
            )
            (root / ".platform_queue").mkdir(parents=True, exist_ok=True)
            q = root / ".platform_queue" / "next_task.json"
            q.write_text('{"instruction":"keep"}', encoding="utf-8")
            before = hashlib.sha256(q.read_bytes()).hexdigest()
            generate_portfolio_governance_health_report(base_dir=root)
            after = hashlib.sha256(q.read_bytes()).hexdigest()
            self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()

