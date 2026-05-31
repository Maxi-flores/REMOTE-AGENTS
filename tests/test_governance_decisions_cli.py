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

from governance_decisions.cli import main  # noqa: E402


class TestGovernanceDecisionsCLI(unittest.TestCase):
    def _seed_packets(self, root: Path) -> str:
        pdir = root / ".control_plane" / "governance_approval_packets"
        pdir.mkdir(parents=True, exist_ok=True)
        packet_id = "packet_1"
        (pdir / "latest.json").write_text(
            json.dumps(
                {
                    "report_id": "pr1",
                    "packets": [
                        {
                            "packet_id": packet_id,
                            "source_dossier_id": "d1",
                            "approval_status": "ready_for_review",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        return packet_id

    def test_print(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._seed_packets(root)
            out = io.StringIO()
            rc = main(["--print", "--base-dir", str(root)], stdout=out)
            self.assertEqual(rc, 0)
            self.assertIn("Governance Decision Summary", out.getvalue())

    def test_record_decision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packet_id = self._seed_packets(root)
            rc = main(
                [
                    "--record-decision",
                    "--base-dir",
                    str(root),
                    "--packet-id",
                    packet_id,
                    "--decision",
                    "defer",
                    "--reviewer",
                    "Max",
                    "--notes",
                    "Later",
                ]
            )
            self.assertEqual(rc, 0)
            decisions = root / ".control_plane" / "governance_decisions" / "decisions.json"
            self.assertTrue(decisions.exists())

    def test_approve_requires_ack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packet_id = self._seed_packets(root)
            rc = main(
                [
                    "--record-decision",
                    "--base-dir",
                    str(root),
                    "--packet-id",
                    packet_id,
                    "--decision",
                    "approve_for_manual_execution",
                    "--reviewer",
                    "Max",
                    "--notes",
                    "ok",
                ]
            )
            self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()

