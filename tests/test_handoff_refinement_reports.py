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

from handoff_refinement.reports import (  # noqa: E402
    append_refinement_report_jsonl,
    write_refinement_report,
    write_timestamped_refinement_report,
)


class TestHandoffRefinementReports(unittest.TestCase):
    def test_report_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = {"report_id": "r1"}
            a = write_refinement_report(payload, path=root / ".control_plane" / "handoff_refinements" / "latest.json")
            b = write_timestamped_refinement_report(payload, directory=root / ".control_plane" / "handoff_refinements")
            c = append_refinement_report_jsonl(payload, path=root / ".control_plane" / "handoff_refinements" / "history.jsonl")
            self.assertTrue(a.exists() and b.exists() and c.exists())
            self.assertEqual(json.loads(c.read_text(encoding="utf-8").splitlines()[0])["report_id"], "r1")


if __name__ == "__main__":
    unittest.main()
