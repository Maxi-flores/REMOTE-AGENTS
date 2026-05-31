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

from execution_dossier.reports import (  # noqa: E402
    append_execution_dossier_report_jsonl,
    write_execution_dossier_report,
    write_timestamped_execution_dossier_report,
)


class TestExecutionDossierReports(unittest.TestCase):
    def test_writes_under_expected_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = {"report_id": "r1"}
            a = write_execution_dossier_report(payload, path=root / ".control_plane" / "execution_dossiers" / "latest.json")
            b = write_timestamped_execution_dossier_report(payload, directory=root / ".control_plane" / "execution_dossiers")
            c = append_execution_dossier_report_jsonl(payload, path=root / ".control_plane" / "execution_dossiers" / "history.jsonl")
            self.assertTrue(a.exists() and b.exists() and c.exists())
            self.assertEqual(json.loads(c.read_text(encoding="utf-8").splitlines()[0])["report_id"], "r1")


if __name__ == "__main__":
    unittest.main()
