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

from release_readiness.cli import main  # noqa: E402


class TestReleaseReadinessCli(unittest.TestCase):
    def _seed(self, base: Path) -> Path:
        cp = base / ".control_plane"
        cp.mkdir(parents=True, exist_ok=True)
        snapshot = cp / "snapshot.json"
        snapshot.write_text(json.dumps({"snapshot_id": "s1", "schema_version": 1}), encoding="utf-8")
        return snapshot

    def test_cli_print_export_check_file_modes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            snapshot = self._seed(base)
            out = io.StringIO()
            code = main(["--print", "--base-dir", tmp], stdout=out)
            self.assertEqual(code, 0)
            payload = json.loads(out.getvalue())
            self.assertIn("report_id", payload)

            out = io.StringIO()
            code = main(["--check-file", str(snapshot), "--artifact-type", "control_plane_snapshot"], stdout=out)
            self.assertEqual(code, 0)
            payload = json.loads(out.getvalue())
            self.assertIn("findings", payload)

            out = io.StringIO()
            code = main(["--export", "--base-dir", tmp], stdout=out)
            self.assertEqual(code, 0)
            self.assertTrue((base / ".release_reports" / "release_readiness.json").exists())

            out = io.StringIO()
            code = main(["--export-jsonl", "--base-dir", tmp], stdout=out)
            self.assertEqual(code, 0)
            self.assertTrue((base / ".release_reports" / "release_readiness.jsonl").exists())

    def test_source_artifacts_not_modified(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            snapshot = self._seed(base)
            before = snapshot.read_text(encoding="utf-8")
            _ = main(["--check-file", str(snapshot), "--artifact-type", "control_plane_snapshot"], stdout=io.StringIO())
            after = snapshot.read_text(encoding="utf-8")
            self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()

