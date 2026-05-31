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

from governance_approval_packets.cli import main  # noqa: E402


class TestGovernanceApprovalPacketsCLI(unittest.TestCase):
    def test_print(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".control_plane" / "governance_approval_readiness").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "governance_recovery_dossiers").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "governance_approval_readiness" / "latest.json").write_text(json.dumps({"report_id": "rr1", "records": []}), encoding="utf-8")
            (root / ".control_plane" / "governance_recovery_dossiers" / "latest.json").write_text(json.dumps({"report_id": "dr1", "dossiers": []}), encoding="utf-8")
            out = io.StringIO()
            rc = main(["--print", "--base-dir", str(root)], stdout=out)
            self.assertEqual(rc, 0)
            self.assertIn("Governance Approval Packets", out.getvalue())

    def test_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".control_plane" / "governance_approval_readiness").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "governance_recovery_dossiers").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "governance_approval_readiness" / "latest.json").write_text(json.dumps({"report_id": "rr1", "records": []}), encoding="utf-8")
            (root / ".control_plane" / "governance_recovery_dossiers" / "latest.json").write_text(json.dumps({"report_id": "dr1", "dossiers": []}), encoding="utf-8")
            rc = main(["--export", "--export-jsonl", "--base-dir", str(root)])
            self.assertEqual(rc, 0)
            self.assertTrue((root / ".control_plane" / "governance_approval_packets" / "latest.json").exists())
            self.assertTrue((root / ".control_plane" / "governance_approval_packets" / "history.jsonl").exists())


if __name__ == "__main__":
    unittest.main()

