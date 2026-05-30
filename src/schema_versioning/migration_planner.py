from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

from schema_versioning.checker import check_artifact_file, detect_artifact_version
from schema_versioning.contracts import MigrationPlan, new_id


def plan_control_plane_snapshot_migration(snapshot: Dict[str, Any], target_version: int = 1) -> Dict[str, Any]:
    detected = detect_artifact_version(snapshot)
    return _plan(
        artifact_type="control_plane_snapshot",
        artifact_path="<in-memory>",
        detected_version=detected,
        target_version=target_version,
    )


def plan_sentient_ui_view_model_migration(view_model: Dict[str, Any], target_version: int = 1) -> Dict[str, Any]:
    detected = detect_artifact_version(view_model)
    return _plan(
        artifact_type="sentient_ui_view_model",
        artifact_path="<in-memory>",
        detected_version=detected,
        target_version=target_version,
    )


def plan_artifact_file_migration(path: str | Path, artifact_type: str, target_version: int = 1) -> Dict[str, Any]:
    result = check_artifact_file(path, artifact_type=artifact_type)
    return _plan(
        artifact_type=artifact_type,
        artifact_path=str(path),
        detected_version=result.get("detected_version"),
        target_version=target_version,
    )


def write_migration_dry_run_report(plan: Dict[str, Any], output_dir: str | Path = ".schema_migrations") -> Path:
    output_root = Path(output_dir)
    normalized = str(output_root).replace("\\", "/")
    if "/.schema_migrations" not in f"/{normalized}":
        raise ValueError("output_dir must be under .schema_migrations")
    output_root.mkdir(parents=True, exist_ok=True)
    filename = f"{plan.get('plan_id', new_id('migration'))}.json"
    out_path = output_root / filename
    tmp = out_path.with_name(f".{out_path.name}.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(plan, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, out_path)
    return out_path


def _plan(
    *,
    artifact_type: str,
    artifact_path: str,
    detected_version: Any,
    target_version: int,
) -> Dict[str, Any]:
    if isinstance(detected_version, int) and detected_version == target_version:
        status = "not_required"
        steps = ["No migration required; artifact already at target schema version."]
    elif isinstance(detected_version, int):
        status = "dry_run_only"
        steps = [
            f"Prepare mapping from schema_version={detected_version} to schema_version={target_version}.",
            "Validate required fields and compatibility constraints.",
            "Do not rewrite artifact in Phase 10.",
        ]
    elif detected_version is None:
        status = "blocked"
        steps = ["Unable to determine source schema version.", "Manual inspection required before migration planning."]
    else:
        status = "unsupported"
        steps = ["Unsupported source schema version format."]
    return MigrationPlan(
        plan_id=new_id("migration_plan"),
        artifact_type=artifact_type,  # type: ignore[arg-type]
        artifact_path=artifact_path,
        from_version=detected_version if isinstance(detected_version, int) else None,
        to_version=target_version,
        migration_status=status,  # type: ignore[arg-type]
        steps=steps,
        destructive=False,
        metadata={"phase": 10, "dry_run_only": True},
    ).to_dict()

