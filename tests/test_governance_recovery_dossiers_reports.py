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

from governance_recovery_dossiers.reports import (  # noqa: E402
    append_governance_recovery_dossier_report_jsonl,
    write_governance_recovery_dossier_report,
    write_timestamped_governance_recovery_dossier_report,
)


class TestGovernanceRecoveryDossiersReports(unittest.TestCase):
    def test_report_writes_under_allowed_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            report = {"report_id": "r1"}
            out = write_governance_recovery_dossier_report(
                report,
                path=base / ".control_plane" / "governance_recovery_dossiers" / "latest.json",
            )
            self.assertTrue(out.exists())
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(payload["report_id"], "r1")

    def test_jsonl_append(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            p = append_governance_recovery_dossier_report_jsonl(
                {"report_id": "r1"},
                path=base / ".control_plane" / "governance_recovery_dossiers" / "history.jsonl",
            )
            lines = p.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(lines), 1)

    def test_timestamped_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = write_timestamped_governance_recovery_dossier_report(
                {"report_id": "r1"},
                directory=Path(tmp) / ".control_plane" / "governance_recovery_dossiers",
            )
            self.assertTrue(out.name.startswith("report_"))


if __name__ == "__main__":
    unittest.main()

