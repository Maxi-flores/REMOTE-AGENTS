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

from schema_versioning.cli import main  # noqa: E402


class TestSchemaVersioningCli(unittest.TestCase):
    def test_cli_check_modes_print_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            cp = base / ".control_plane"
            cp.mkdir(parents=True, exist_ok=True)
            cp_snapshot = {
                "snapshot_id": "s1",
                "generated_utc": "2026-01-01T00:00:00Z",
                "schema_version": 1,
                "runtime": {},
                "missions": {},
                "agents": {},
                "repositories": {},
                "tools": {},
                "scheduler": {},
                "memory_graph": {},
                "approvals": {},
                "consensus": {},
                "queue": {},
                "observability": {},
                "metadata": {},
            }
            (cp / "snapshot.json").write_text(json.dumps(cp_snapshot), encoding="utf-8")
            out = io.StringIO()
            code = main(["--check-control-plane", "--base-dir", tmp], stdout=out)
            self.assertEqual(code, 0)
            payload = json.loads(out.getvalue())
            self.assertIn("is_compatible", payload)

    def test_cli_dry_run_writes_only_schema_migrations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            su = base / ".sentient_ui"
            su.mkdir(parents=True, exist_ok=True)
            artifact = su / "view_model.json"
            artifact.write_text(json.dumps({"schema_version": 1}), encoding="utf-8")
            out = io.StringIO()
            code = main(
                [
                    "--plan-migration",
                    str(artifact),
                    "--artifact-type",
                    "sentient_ui_view_model",
                    "--dry-run",
                    "--base-dir",
                    tmp,
                ],
                stdout=out,
            )
            self.assertEqual(code, 0)
            payload = json.loads(out.getvalue())
            report = Path(payload["dry_run_report_path"])
            self.assertTrue(report.exists())
            self.assertIn(".schema_migrations", str(report))

    def test_source_artifacts_not_modified(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            cp = base / ".control_plane"
            cp.mkdir(parents=True, exist_ok=True)
            snapshot = cp / "snapshot.json"
            snapshot.write_text(json.dumps({"schema_version": 1}), encoding="utf-8")
            before = snapshot.read_text(encoding="utf-8")
            _ = main(
                [
                    "--check-file",
                    str(snapshot),
                    "--artifact-type",
                    "control_plane_snapshot",
                    "--base-dir",
                    tmp,
                ],
                stdout=io.StringIO(),
            )
            after = snapshot.read_text(encoding="utf-8")
            self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()

