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

from schema_versioning.migration_planner import (  # noqa: E402
    plan_artifact_file_migration,
    plan_control_plane_snapshot_migration,
    write_migration_dry_run_report,
)


class TestSchemaVersioningMigrationPlanner(unittest.TestCase):
    def test_planner_returns_not_required_for_v1_artifacts(self) -> None:
        plan = plan_control_plane_snapshot_migration({"schema_version": 1}, target_version=1)
        self.assertEqual(plan["migration_status"], "not_required")

    def test_planner_blocks_unknown_versions(self) -> None:
        plan = plan_control_plane_snapshot_migration({}, target_version=1)
        self.assertEqual(plan["migration_status"], "blocked")

    def test_dry_run_report_writes_only_under_schema_migrations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plan = {
                "plan_id": "p1",
                "artifact_type": "control_plane_snapshot",
                "artifact_path": ".control_plane/snapshot.json",
                "from_version": 1,
                "to_version": 1,
                "migration_status": "not_required",
                "steps": ["none"],
                "destructive": False,
                "created_utc": "2026-01-01T00:00:00Z",
                "metadata": {},
            }
            path = write_migration_dry_run_report(plan, output_dir=Path(tmp) / ".schema_migrations")
            self.assertTrue(path.exists())
            self.assertIn(".schema_migrations", str(path))
            with self.assertRaises(ValueError):
                write_migration_dry_run_report(plan, output_dir=Path(tmp) / "reports")


if __name__ == "__main__":
    unittest.main()

