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

from remediation_handoff.reports import (  # noqa: E402
    append_implementation_package_report_jsonl,
    write_implementation_package_report,
    write_timestamped_implementation_package_report,
)


class TestRemediationHandoffReports(unittest.TestCase):
    def test_writes_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = {"report_id": "r1", "packages": []}
            p1 = write_implementation_package_report(report, path=root / ".control_plane" / "remediation_handoffs" / "latest.json")
            self.assertTrue(p1.exists())
            p2 = write_timestamped_implementation_package_report(report, directory=root / ".control_plane" / "remediation_handoffs")
            self.assertTrue(p2.exists())
            p3 = append_implementation_package_report_jsonl(report, path=root / ".control_plane" / "remediation_handoffs" / "history.jsonl")
            rows = p3.read_text(encoding="utf-8").splitlines()
            self.assertEqual(json.loads(rows[0])["report_id"], "r1")


if __name__ == "__main__":
    unittest.main()
