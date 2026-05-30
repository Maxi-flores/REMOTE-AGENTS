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

from control_plane.orchestrator_cli import main  # noqa: E402


class TestControlPlaneOrchestratorCli(unittest.TestCase):
    def test_print_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = io.StringIO()
            code = main(["--print", "--base-dir", tmp], stdout=out)
            self.assertEqual(code, 0)
            payload = json.loads(out.getvalue())
            self.assertIn("report", payload)
            self.assertTrue(payload["report"]["advisory_only"])

    def test_export_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            code = main(["--export", "--base-dir", tmp], stdout=io.StringIO())
            self.assertEqual(code, 0)
            self.assertTrue((base / ".control_plane" / "orchestration" / "orchestration_report.json").exists())

    def test_export_jsonl_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            code = main(["--export-jsonl", "--base-dir", tmp], stdout=io.StringIO())
            self.assertEqual(code, 0)
            self.assertTrue((base / ".control_plane" / "orchestration" / "orchestration_reports.jsonl").exists())

    def test_bootstrap_artifacts_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            out = io.StringIO()
            code = main(["--bootstrap-artifacts", "--base-dir", tmp], stdout=out)
            self.assertEqual(code, 0)
            payload = json.loads(out.getvalue())
            self.assertIn("bootstrap", payload)
            self.assertTrue((base / ".control_plane" / "snapshot.json").exists())
            self.assertTrue((base / ".sentient_ui" / "view_model.json").exists())


if __name__ == "__main__":
    unittest.main()
