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

from governance_approval_packets.reports import (  # noqa: E402
    append_governance_approval_packet_report_jsonl,
    write_governance_approval_packet_report,
    write_timestamped_governance_approval_packet_report,
)


class TestGovernanceApprovalPacketsReports(unittest.TestCase):
    def test_write_and_read(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = write_governance_approval_packet_report(
                {"report_id": "r1"},
                path=Path(tmp) / ".control_plane" / "governance_approval_packets" / "latest.json",
            )
            self.assertEqual(json.loads(p.read_text(encoding="utf-8"))["report_id"], "r1")

    def test_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = append_governance_approval_packet_report_jsonl(
                {"report_id": "r1"},
                path=Path(tmp) / ".control_plane" / "governance_approval_packets" / "history.jsonl",
            )
            self.assertEqual(len(p.read_text(encoding="utf-8").splitlines()), 1)

    def test_timestamped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = write_timestamped_governance_approval_packet_report(
                {"report_id": "r1"},
                directory=Path(tmp) / ".control_plane" / "governance_approval_packets",
            )
            self.assertTrue(p.name.startswith("report_"))


if __name__ == "__main__":
    unittest.main()

