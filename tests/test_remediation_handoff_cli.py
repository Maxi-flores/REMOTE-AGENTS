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

from remediation_handoff.cli import main  # noqa: E402


class TestRemediationHandoffCli(unittest.TestCase):
    def test_print_and_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            d = root / ".control_plane" / "remediation_plans"
            d.mkdir(parents=True, exist_ok=True)
            (d / "latest.json").write_text(json.dumps({"report_id": "rr", "batches": [], "items": []}), encoding="utf-8")
            stdout = io.StringIO()
            rc = main(["--print", "--export", "--export-jsonl", "--base-dir", str(root)], stdout=stdout)
            self.assertEqual(rc, 0)
            self.assertIn("Implementation Packages", stdout.getvalue())
            self.assertTrue((root / ".control_plane" / "remediation_handoffs" / "latest.json").exists())


if __name__ == "__main__":
    unittest.main()
