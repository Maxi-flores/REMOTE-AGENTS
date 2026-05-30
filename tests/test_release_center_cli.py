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

from release_center.cli import main  # noqa: E402


class TestReleaseCenterCli(unittest.TestCase):
    def _seed(self, base: Path) -> Path:
        rr = base / ".release_reports"
        rr.mkdir(parents=True, exist_ok=True)
        readiness = rr / "release_readiness.json"
        readiness.write_text(
            json.dumps(
                {
                    "report_id": "rr1",
                    "readiness_score": 91,
                    "readiness_status": "ready",
                    "blockers": [],
                    "warnings": [],
                }
            ),
            encoding="utf-8",
        )
        return readiness

    def test_cli_print_export_modes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            readiness = self._seed(base)
            before = readiness.read_text(encoding="utf-8")
            out = io.StringIO()
            code = main(["--print", "--base-dir", tmp], stdout=out)
            self.assertEqual(code, 0)
            payload = json.loads(out.getvalue())
            self.assertIn("report", payload)

            out = io.StringIO()
            code = main(["--export", "--base-dir", tmp], stdout=out)
            self.assertEqual(code, 0)
            self.assertTrue((base / ".release_reports" / "release_timeline.json").exists())

            out = io.StringIO()
            code = main(["--export-jsonl", "--base-dir", tmp], stdout=out)
            self.assertEqual(code, 0)
            self.assertTrue((base / ".release_reports" / "release_timeline.jsonl").exists())
            after = readiness.read_text(encoding="utf-8")
            self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()

