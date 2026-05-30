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

from release_readiness.reports import (  # noqa: E402
    append_release_readiness_report_jsonl,
    build_full_release_readiness_report,
    write_release_readiness_report,
)


class TestReleaseReadinessReports(unittest.TestCase):
    def _seed_artifacts(self, base: Path) -> None:
        cp = base / ".control_plane"
        su = base / ".sentient_ui"
        cp.mkdir(parents=True, exist_ok=True)
        su.mkdir(parents=True, exist_ok=True)
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
        su_snapshot = {
            "view_model_id": "v1",
            "generated_utc": "2026-01-01T00:00:00Z",
            "source_snapshot_id": "s1",
            "schema_version": 1,
            "runtime_panel": {},
            "mission_panel": {},
            "agent_panel": {},
            "repository_panel": {},
            "tool_panel": {},
            "scheduler_panel": {},
            "memory_panel": {},
            "approval_panel": {},
            "consensus_panel": {},
            "observability_panel": {},
            "alerts": [],
            "metadata": {},
        }
        (cp / "snapshot.json").write_text(json.dumps(cp_snapshot), encoding="utf-8")
        (cp / "snapshots.jsonl").write_text(json.dumps(cp_snapshot) + "\n", encoding="utf-8")
        (su / "view_model.json").write_text(json.dumps(su_snapshot), encoding="utf-8")
        (su / "view_models.jsonl").write_text(json.dumps(su_snapshot) + "\n", encoding="utf-8")

    def test_full_report_includes_checked_artifacts_and_findings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self._seed_artifacts(base)
            report = build_full_release_readiness_report(base)
            self.assertIn("checked_artifacts", report)
            self.assertIn("findings", report)
            self.assertGreater(len(report["checked_artifacts"]), 0)

    def test_report_writer_writes_only_under_release_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self._seed_artifacts(base)
            out = base / ".release_reports" / "release_readiness.json"
            report = write_release_readiness_report(out, base_dir=base)
            self.assertTrue(out.exists())
            self.assertIn(".release_reports", str(out))
            with self.assertRaises(ValueError):
                write_release_readiness_report(base / "release_readiness.json", base_dir=base)

    def test_jsonl_report_appends_valid_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self._seed_artifacts(base)
            out = base / ".release_reports" / "release_readiness.jsonl"
            append_release_readiness_report_jsonl(out, base_dir=base)
            append_release_readiness_report_jsonl(out, base_dir=base)
            lines = [line for line in out.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(len(lines), 2)
            for line in lines:
                payload = json.loads(line)
                self.assertIn("report_id", payload)


if __name__ == "__main__":
    unittest.main()

