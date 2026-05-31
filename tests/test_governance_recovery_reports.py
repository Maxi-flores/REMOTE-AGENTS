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

from governance_recovery.reports import append_governance_recovery_report_jsonl, write_governance_recovery_report  # noqa: E402


class TestGovernanceRecoveryReports(unittest.TestCase):
    def test_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = write_governance_recovery_report({"report_id": "r1"}, path=root / ".control_plane" / "governance_recovery" / "latest.json")
            self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["report_id"], "r1")
            out2 = append_governance_recovery_report_jsonl({"report_id": "r2"}, path=root / ".control_plane" / "governance_recovery" / "history.jsonl")
            self.assertEqual(len(out2.read_text(encoding="utf-8").splitlines()), 1)


if __name__ == "__main__":
    unittest.main()

