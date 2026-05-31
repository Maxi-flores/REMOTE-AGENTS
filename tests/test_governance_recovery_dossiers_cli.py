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

from governance_recovery_dossiers.cli import main  # noqa: E402


class TestGovernanceRecoveryDossiersCLI(unittest.TestCase):
    def test_cli_print(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            recovery_dir = root / ".control_plane" / "governance_recovery"
            recovery_dir.mkdir(parents=True, exist_ok=True)
            (recovery_dir / "latest.json").write_text(
                json.dumps({"report_id": "gr1", "actions": [], "waves": []}),
                encoding="utf-8",
            )
            out = io.StringIO()
            rc = main(["--print", "--base-dir", str(root)], stdout=out)
            self.assertEqual(rc, 0)
            self.assertIn("Governance Recovery Dossiers", out.getvalue())

    def test_cli_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            recovery_dir = root / ".control_plane" / "governance_recovery"
            recovery_dir.mkdir(parents=True, exist_ok=True)
            (recovery_dir / "latest.json").write_text(
                json.dumps({"report_id": "gr1", "actions": [], "waves": []}),
                encoding="utf-8",
            )
            rc = main(["--export", "--export-jsonl", "--base-dir", str(root)])
            self.assertEqual(rc, 0)
            self.assertTrue((root / ".control_plane" / "governance_recovery_dossiers" / "latest.json").exists())
            self.assertTrue((root / ".control_plane" / "governance_recovery_dossiers" / "history.jsonl").exists())


if __name__ == "__main__":
    unittest.main()

