from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from control_plane.contracts import validate_control_plane_snapshot_dict
from schema_versioning.contracts import (
    CompatibilityCheckResult,
    SchemaManifest,
    new_id,
    validate_schema_manifest_dict,
)
from sentient_ui.contracts import validate_view_model_envelope_dict


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTROL_MANIFEST = REPO_ROOT / "config" / "schema_manifests" / "control_plane_snapshot.v1.json"
UI_MANIFEST = REPO_ROOT / "config" / "schema_manifests" / "sentient_ui_view_model.v1.json"


def load_schema_manifest(path: str | Path) -> Dict[str, Any]:
    manifest_path = Path(path)
    with manifest_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        raise ValueError("manifest must be an object")
    validate_schema_manifest_dict(payload)
    return payload


def detect_artifact_version(artifact: Dict[str, Any]) -> int | None:
    version = artifact.get("schema_version")
    if isinstance(version, bool):
        return None
    if isinstance(version, int):
        return version
    try:
        return int(version)
    except Exception:
        return None


def check_control_plane_snapshot_compatibility(
    snapshot: Dict[str, Any],
    manifest: Dict[str, Any] | None = None,
    *,
    artifact_path: str = "<in-memory>",
) -> Dict[str, Any]:
    manifest = manifest or load_schema_manifest(CONTROL_MANIFEST)
    return _check_artifact_against_manifest(
        snapshot,
        manifest,
        artifact_path=artifact_path,
        validator=validate_control_plane_snapshot_dict,
    )


def check_sentient_ui_view_model_compatibility(
    view_model: Dict[str, Any],
    manifest: Dict[str, Any] | None = None,
    *,
    artifact_path: str = "<in-memory>",
) -> Dict[str, Any]:
    manifest = manifest or load_schema_manifest(UI_MANIFEST)
    return _check_artifact_against_manifest(
        view_model,
        manifest,
        artifact_path=artifact_path,
        validator=validate_view_model_envelope_dict,
    )


def check_artifact_file(path: str | Path, artifact_type: str | None = None) -> Dict[str, Any]:
    artifact_path = Path(path)
    resolved_type = artifact_type or _infer_artifact_type_from_path(artifact_path)
    if not artifact_path.exists():
        return _result(
            artifact_type=resolved_type or "control_plane_snapshot",
            artifact_path=str(artifact_path),
            detected_version=None,
            expected_version=None,
            is_compatible=False,
            issues=["artifact file missing"],
            warnings=[],
        )
    try:
        with artifact_path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception as exc:
        return _result(
            artifact_type=resolved_type or "control_plane_snapshot",
            artifact_path=str(artifact_path),
            detected_version=None,
            expected_version=None,
            is_compatible=False,
            issues=[f"malformed JSON: {exc}"],
            warnings=[],
        )
    if not isinstance(payload, dict):
        return _result(
            artifact_type=resolved_type or "control_plane_snapshot",
            artifact_path=str(artifact_path),
            detected_version=None,
            expected_version=None,
            is_compatible=False,
            issues=["artifact JSON root must be an object"],
            warnings=[],
        )
    if resolved_type == "control_plane_snapshot":
        return check_control_plane_snapshot_compatibility(payload, artifact_path=str(artifact_path))
    if resolved_type == "sentient_ui_view_model":
        return check_sentient_ui_view_model_compatibility(payload, artifact_path=str(artifact_path))
    return _result(
        artifact_type=resolved_type or "control_plane_snapshot",
        artifact_path=str(artifact_path),
        detected_version=detect_artifact_version(payload),
        expected_version=None,
        is_compatible=False,
        issues=["unsupported artifact_type for check_artifact_file"],
        warnings=[],
    )


def check_jsonl_artifact_file(path: str | Path, artifact_type: str) -> Dict[str, Any]:
    artifact_path = Path(path)
    if not artifact_path.exists():
        return _result(
            artifact_type=artifact_type,
            artifact_path=str(artifact_path),
            detected_version=None,
            expected_version=None,
            is_compatible=False,
            issues=["artifact file missing"],
            warnings=[],
            metadata={"line_count": 0, "invalid_lines": 0},
        )
    valid = 0
    invalid = 0
    versions: List[int] = []
    issues: List[str] = []
    try:
        with artifact_path.open("r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                raw = line.strip()
                if not raw:
                    continue
                try:
                    payload = json.loads(raw)
                except Exception:
                    invalid += 1
                    issues.append(f"line {line_no}: malformed JSON")
                    continue
                if not isinstance(payload, dict):
                    invalid += 1
                    issues.append(f"line {line_no}: root is not object")
                    continue
                result = (
                    check_control_plane_snapshot_compatibility(payload, artifact_path=f"{artifact_path}:{line_no}")
                    if artifact_type == "control_plane_snapshot_jsonl"
                    else check_sentient_ui_view_model_compatibility(payload, artifact_path=f"{artifact_path}:{line_no}")
                )
                if result.get("is_compatible"):
                    valid += 1
                    detected = result.get("detected_version")
                    if isinstance(detected, int):
                        versions.append(detected)
                else:
                    invalid += 1
                    issues.extend([f"line {line_no}: {issue}" for issue in result.get("issues", [])])
    except Exception as exc:
        return _result(
            artifact_type=artifact_type,
            artifact_path=str(artifact_path),
            detected_version=None,
            expected_version=None,
            is_compatible=False,
            issues=[f"unable to read JSONL: {exc}"],
            warnings=[],
        )

    expected = 1
    detected_version = versions[-1] if versions else None
    return _result(
        artifact_type=artifact_type,
        artifact_path=str(artifact_path),
        detected_version=detected_version,
        expected_version=expected,
        is_compatible=(invalid == 0 and valid > 0),
        issues=issues,
        warnings=[] if valid > 0 else ["no valid records found"],
        metadata={"line_count": valid + invalid, "valid_lines": valid, "invalid_lines": invalid},
    )


def _check_artifact_against_manifest(
    artifact: Dict[str, Any],
    manifest: Dict[str, Any],
    *,
    artifact_path: str,
    validator,
) -> Dict[str, Any]:
    detected_version = detect_artifact_version(artifact)
    expected_version = int(manifest.get("current_version", 1))
    issues: List[str] = []
    warnings: List[str] = []

    for field in manifest.get("required_fields", []):
        if field not in artifact:
            issues.append(f"missing required field: {field}")
    if detected_version is None:
        issues.append("schema_version missing or invalid")
    else:
        supported = [int(v) for v in manifest.get("supported_versions", [])]
        deprecated = [int(v) for v in manifest.get("deprecated_versions", [])]
        if detected_version not in supported:
            issues.append(f"unsupported schema_version: {detected_version}")
        if detected_version in deprecated:
            warnings.append(f"deprecated schema_version: {detected_version}")
    try:
        validator(artifact)
    except Exception as exc:
        issues.append(str(exc))
    return _result(
        artifact_type=manifest.get("artifact_type", "control_plane_snapshot"),
        artifact_path=artifact_path,
        detected_version=detected_version,
        expected_version=expected_version,
        is_compatible=(len(issues) == 0),
        issues=issues,
        warnings=warnings,
    )


def _result(
    *,
    artifact_type: str,
    artifact_path: str,
    detected_version: int | None,
    expected_version: int | None,
    is_compatible: bool,
    issues: List[str],
    warnings: List[str],
    metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    return CompatibilityCheckResult(
        result_id=new_id("compat"),
        artifact_type=artifact_type,  # type: ignore[arg-type]
        artifact_path=artifact_path,
        detected_version=detected_version,
        expected_version=expected_version,
        is_compatible=is_compatible,
        issues=issues,
        warnings=warnings,
        metadata=dict(metadata or {}),
    ).to_dict()


def _infer_artifact_type_from_path(path: Path) -> Optional[str]:
    name = path.name.lower()
    if name == "snapshot.json":
        return "control_plane_snapshot"
    if name == "snapshots.jsonl":
        return "control_plane_snapshot_jsonl"
    if name == "view_model.json":
        return "sentient_ui_view_model"
    if name == "view_models.jsonl":
        return "sentient_ui_view_model_jsonl"
    return None

