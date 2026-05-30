from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from release_readiness.contracts import ContractDriftFinding, new_id
from schema_versioning.checker import (
    CONTROL_MANIFEST,
    UI_MANIFEST,
    check_artifact_file,
    check_jsonl_artifact_file,
    load_schema_manifest,
)


def compare_artifact_to_manifest(
    artifact: Dict[str, Any],
    manifest: Dict[str, Any],
    artifact_type: str,
    artifact_path: str = "",
) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    required = manifest.get("required_fields") if isinstance(manifest.get("required_fields"), list) else []
    optional = manifest.get("optional_fields") if isinstance(manifest.get("optional_fields"), list) else []
    for field in required:
        if field not in artifact:
            findings.append(
                _finding(
                    artifact_type=artifact_type,
                    artifact_path=artifact_path,
                    drift_type="missing_required_field",
                    severity="error",
                    field_path=str(field),
                    expected="present",
                    actual="missing",
                    message=f"Required field missing: {field}",
                )
            )
    known_fields = set(str(v) for v in required + optional)
    for key in artifact.keys():
        if known_fields and key not in known_fields:
            findings.append(
                _finding(
                    artifact_type=artifact_type,
                    artifact_path=artifact_path,
                    drift_type="unexpected_field",
                    severity="info",
                    field_path=str(key),
                    expected="known field",
                    actual="unknown field",
                    message=f"Unexpected field present: {key}",
                )
            )
    supported = [int(v) for v in manifest.get("supported_versions", [])]
    deprecated = [int(v) for v in manifest.get("deprecated_versions", [])]
    version = artifact.get("schema_version")
    if isinstance(version, int):
        if supported and version not in supported:
            findings.append(
                _finding(
                    artifact_type=artifact_type,
                    artifact_path=artifact_path,
                    drift_type="unsupported_version",
                    severity="critical",
                    field_path="schema_version",
                    expected=supported,
                    actual=version,
                    message=f"Unsupported schema_version: {version}",
                )
            )
        if version in deprecated:
            findings.append(
                _finding(
                    artifact_type=artifact_type,
                    artifact_path=artifact_path,
                    drift_type="deprecated_version",
                    severity="warning",
                    field_path="schema_version",
                    expected="non-deprecated version",
                    actual=version,
                    message=f"Deprecated schema_version: {version}",
                )
            )
    return findings


def analyze_control_plane_snapshot(path: str | Path = ".control_plane/snapshot.json") -> List[Dict[str, Any]]:
    return _analyze_json_file(path, "control_plane_snapshot", CONTROL_MANIFEST)


def analyze_sentient_ui_view_model(path: str | Path = ".sentient_ui/view_model.json") -> List[Dict[str, Any]]:
    return _analyze_json_file(path, "sentient_ui_view_model", UI_MANIFEST)


def analyze_control_plane_jsonl(path: str | Path = ".control_plane/snapshots.jsonl") -> List[Dict[str, Any]]:
    return _analyze_jsonl(path, "control_plane_snapshot_jsonl")


def analyze_sentient_ui_jsonl(path: str | Path = ".sentient_ui/view_models.jsonl") -> List[Dict[str, Any]]:
    return _analyze_jsonl(path, "sentient_ui_view_model_jsonl")


def analyze_schema_manifest(path: str | Path) -> List[Dict[str, Any]]:
    manifest_path = Path(path)
    if not manifest_path.exists():
        return [
            _finding(
                artifact_type="schema_manifest",
                artifact_path=str(manifest_path),
                drift_type="schema_manifest_missing",
                severity="error",
                field_path="",
                expected="manifest file",
                actual="missing",
                message="Schema manifest file missing",
            )
        ]
    try:
        _ = load_schema_manifest(manifest_path)
    except Exception as exc:
        return [
            _finding(
                artifact_type="schema_manifest",
                artifact_path=str(manifest_path),
                drift_type="malformed_artifact",
                severity="error",
                field_path="",
                expected="valid manifest json",
                actual="invalid",
                message=f"Schema manifest invalid: {exc}",
            )
        ]
    return []


def _analyze_json_file(path: str | Path, artifact_type: str, manifest_path: Path) -> List[Dict[str, Any]]:
    artifact_path = Path(path)
    if not artifact_path.exists():
        return [
            _finding(
                artifact_type=artifact_type,
                artifact_path=str(artifact_path),
                drift_type="missing_artifact",
                severity="critical",
                field_path="",
                expected="artifact file",
                actual="missing",
                message="Artifact file missing",
            )
        ]
    try:
        with artifact_path.open("r", encoding="utf-8") as f:
            artifact = json.load(f)
    except Exception as exc:
        return [
            _finding(
                artifact_type=artifact_type,
                artifact_path=str(artifact_path),
                drift_type="malformed_artifact",
                severity="critical",
                field_path="",
                expected="valid JSON object",
                actual="invalid JSON",
                message=f"Malformed artifact JSON: {exc}",
            )
        ]
    if not isinstance(artifact, dict):
        return [
            _finding(
                artifact_type=artifact_type,
                artifact_path=str(artifact_path),
                drift_type="malformed_artifact",
                severity="critical",
                field_path="",
                expected="JSON object",
                actual=type(artifact).__name__,
                message="Artifact root must be an object",
            )
        ]

    findings = []
    manifest = load_schema_manifest(manifest_path)
    findings.extend(compare_artifact_to_manifest(artifact, manifest, artifact_type, str(artifact_path)))
    compat = check_artifact_file(artifact_path, artifact_type=artifact_type)
    for issue in compat.get("issues", []):
        findings.append(
            _finding(
                artifact_type=artifact_type,
                artifact_path=str(artifact_path),
                drift_type="compatibility_warning" if "missing required field" not in issue else "missing_required_field",
                severity="error",
                field_path="",
                expected="compatible",
                actual="incompatible",
                message=str(issue),
            )
        )
    for warning in compat.get("warnings", []):
        findings.append(
            _finding(
                artifact_type=artifact_type,
                artifact_path=str(artifact_path),
                drift_type="compatibility_warning",
                severity="warning",
                field_path="",
                expected="no warning",
                actual="warning",
                message=str(warning),
            )
        )
    return findings


def _analyze_jsonl(path: str | Path, artifact_type: str) -> List[Dict[str, Any]]:
    artifact_path = Path(path)
    if not artifact_path.exists():
        return [
            _finding(
                artifact_type=artifact_type,
                artifact_path=str(artifact_path),
                drift_type="missing_artifact",
                severity="error",
                field_path="",
                expected="jsonl artifact",
                actual="missing",
                message="JSONL artifact missing",
            )
        ]
    result = check_jsonl_artifact_file(artifact_path, artifact_type)
    findings: List[Dict[str, Any]] = []
    for issue in result.get("issues", []):
        findings.append(
            _finding(
                artifact_type=artifact_type,
                artifact_path=str(artifact_path),
                drift_type="jsonl_line_invalid" if "line " in str(issue) else "compatibility_warning",
                severity="error",
                field_path="",
                expected="valid JSONL line",
                actual="invalid line",
                message=str(issue),
            )
        )
    for warning in result.get("warnings", []):
        findings.append(
            _finding(
                artifact_type=artifact_type,
                artifact_path=str(artifact_path),
                drift_type="compatibility_warning",
                severity="warning",
                field_path="",
                expected="no warning",
                actual="warning",
                message=str(warning),
            )
        )
    return findings


def _finding(
    *,
    artifact_type: str,
    artifact_path: str,
    drift_type: str,
    severity: str,
    field_path: str,
    expected: Any,
    actual: Any,
    message: str,
) -> Dict[str, Any]:
    return ContractDriftFinding(
        finding_id=new_id("drift"),
        artifact_type=artifact_type,
        artifact_path=artifact_path,
        drift_type=drift_type,  # type: ignore[arg-type]
        severity=severity,  # type: ignore[arg-type]
        field_path=field_path,
        expected=expected,
        actual=actual,
        message=message,
    ).to_dict()

