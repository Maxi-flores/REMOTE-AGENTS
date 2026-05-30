from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from schema_versioning.contracts import (  # noqa: E402
    CompatibilityCheckResult,
    MigrationPlan,
    SchemaManifest,
    validate_compatibility_check_result_dict,
    validate_migration_plan_dict,
    validate_schema_manifest_dict,
)


class TestSchemaVersioningContracts(unittest.TestCase):
    def test_valid_schema_manifest_passes_validation(self) -> None:
        payload = SchemaManifest(
            schema_id="control_plane_snapshot.v1",
            artifact_type="control_plane_snapshot",
            current_version=1,
            supported_versions=[1],
            deprecated_versions=[],
            required_fields=["snapshot_id"],
            optional_fields=[],
            compatibility_notes=["ok"],
        ).to_dict()
        validate_schema_manifest_dict(payload)

    def test_invalid_artifact_type_fails_validation(self) -> None:
        payload = SchemaManifest(
            schema_id="x",
            artifact_type="control_plane_snapshot",
            current_version=1,
            supported_versions=[1],
            required_fields=[],
            optional_fields=[],
            compatibility_notes=[],
        ).to_dict()
        payload["artifact_type"] = "mystery"
        with self.assertRaises(ValueError):
            validate_schema_manifest_dict(payload)

    def test_valid_compatibility_check_result_passes_validation(self) -> None:
        payload = CompatibilityCheckResult(
            result_id="r1",
            artifact_type="control_plane_snapshot",
            artifact_path=".control_plane/snapshot.json",
            detected_version=1,
            expected_version=1,
            is_compatible=True,
        ).to_dict()
        validate_compatibility_check_result_dict(payload)

    def test_valid_migration_plan_passes_validation(self) -> None:
        payload = MigrationPlan(
            plan_id="p1",
            artifact_type="sentient_ui_view_model",
            artifact_path=".sentient_ui/view_model.json",
            from_version=1,
            to_version=1,
            migration_status="not_required",
            steps=["none"],
            destructive=False,
        ).to_dict()
        validate_migration_plan_dict(payload)

    def test_manifests_parse_successfully(self) -> None:
        for path in (
            REPO_ROOT / "config" / "schema_manifests" / "control_plane_snapshot.v1.json",
            REPO_ROOT / "config" / "schema_manifests" / "sentient_ui_view_model.v1.json",
        ):
            with self.subTest(path=str(path)):
                payload = json.loads(path.read_text(encoding="utf-8"))
                validate_schema_manifest_dict(payload)


if __name__ == "__main__":
    unittest.main()

