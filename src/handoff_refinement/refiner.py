from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from handoff_refinement.contracts import (
    RefinementReport,
    RefinedImplementationPackage,
    new_id,
    utc_now,
    validate_refinement_report_dict,
)
from handoff_refinement.grouping import detect_broad_package, split_groups


def load_handoff_report(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def generate_refinement_report(
    *,
    handoff_report: Dict[str, Any] | None = None,
    handoff_report_path: str | Path | None = None,
    base_dir: str | Path = ".",
    limit: int | None = None,
) -> Dict[str, Any]:
    root = Path(base_dir)
    source_path = Path(handoff_report_path) if handoff_report_path else None
    if handoff_report is None:
        if source_path is None:
            source_path = root / ".control_plane" / "remediation_handoffs" / "latest.json"
        handoff_report = load_handoff_report(source_path)
    refined = _refine_packages(handoff_report.get("packages", []))
    if isinstance(limit, int) and limit > 0:
        refined = refined[:limit]
    split_summary = _build_split_summary(handoff_report.get("packages", []), refined)
    report = RefinementReport(
        report_id=new_id("handoff_refinement_report"),
        generated_utc=utc_now(),
        source_handoff_report_id=str(handoff_report.get("report_id") or "handoff_report_missing"),
        refined_packages=refined,
        split_summary=split_summary,
        advisory_only=True,
        metadata={
            "advisory_only": True,
            "source_report_path": str(source_path) if source_path else None,
            "base_dir": str(root),
        },
    ).to_dict()
    validate_refinement_report_dict(report)
    return report


def _refine_packages(packages: Any) -> List[Dict[str, Any]]:
    if not isinstance(packages, list):
        return []
    refined: List[Dict[str, Any]] = []
    for package in packages:
        if not isinstance(package, dict):
            continue
        is_broad, details = detect_broad_package(package)
        if is_broad:
            refined.extend(_split_package(package, details))
        else:
            refined.append(_copy_as_refined(package, broad=False, details=details))
    return refined


def _split_package(package: Dict[str, Any], details: Dict[str, Any]) -> List[Dict[str, Any]]:
    groups = split_groups(package)
    out: List[Dict[str, Any]] = []
    for (subsystem, change_type), data in sorted(groups.items(), key=lambda x: (x[0][0], x[0][1])):
        files = data.get("target_files", [])
        commands = data.get("validation_commands", []) or ["python -m unittest -v"]
        expected_changes = _extract_expected_changes(package.get("expected_changes", {}), files)
        title = f"{subsystem} {change_type} refinement"
        objective = f"Apply focused changes for subsystem '{subsystem}' with change type '{change_type}'."
        out.append(
            _build_refined_package(
                package=package,
                subsystem=subsystem,
                change_type=change_type,
                title=title,
                objective=objective,
                target_files=files,
                expected_changes=expected_changes,
                validation_commands=commands,
                broad=True,
                details=details,
            )
        )
    return out


def _copy_as_refined(package: Dict[str, Any], *, broad: bool, details: Dict[str, Any]) -> Dict[str, Any]:
    files = _as_list(package.get("target_files"))
    subsystem = _infer_single_or_default(details.get("subsystems", []), "system")
    change_type = _infer_single_or_default(details.get("change_types", []), "add_update")
    return _build_refined_package(
        package=package,
        subsystem=subsystem,
        change_type=change_type,
        title=str(package.get("title") or "Refined package"),
        objective=str(package.get("objective") or "Refined implementation package."),
        target_files=files,
        expected_changes=dict(package.get("expected_changes") or {}),
        validation_commands=_as_list(package.get("validation_commands")) or ["python -m unittest -v"],
        broad=broad,
        details=details,
    )


def _build_refined_package(
    *,
    package: Dict[str, Any],
    subsystem: str,
    change_type: str,
    title: str,
    objective: str,
    target_files: List[str],
    expected_changes: Dict[str, Any],
    validation_commands: List[str],
    broad: bool,
    details: Dict[str, Any],
) -> Dict[str, Any]:
    risk_level = _risk_level_for_scope(target_files, validation_commands, broad)
    estimated_scope = _estimated_scope(target_files, validation_commands)
    traceability = _traceability_refs(package)
    codex_prompt = _build_refined_prompt(
        title=title,
        objective=objective,
        subsystem=subsystem,
        change_type=change_type,
        target_files=target_files,
        expected_changes=expected_changes,
        validation_commands=validation_commands,
        risk_level=risk_level,
    )
    refined = RefinedImplementationPackage(
        refined_package_id=new_id("refined_pkg"),
        source_package_id=str(package.get("package_id") or "unknown_package"),
        source_batch_id=str(package.get("source_batch_id") or "unknown_batch"),
        title=title,
        objective=objective,
        subsystem=subsystem,
        change_type=change_type,
        target_files=target_files,
        expected_changes=expected_changes,
        validation_commands=validation_commands,
        risk_level=risk_level,
        estimated_scope=estimated_scope,
        traceability_refs=traceability,
        codex_prompt=codex_prompt,
        advisory_only=True,
        metadata={
            "advisory_only": True,
            "source_was_broad": broad,
            "broad_reasons": list(details.get("reasons", [])),
        },
    ).to_dict()
    return refined


def _build_refined_prompt(
    *,
    title: str,
    objective: str,
    subsystem: str,
    change_type: str,
    target_files: List[str],
    expected_changes: Dict[str, Any],
    validation_commands: List[str],
    risk_level: str,
) -> Dict[str, Any]:
    lines = [
        "You are implementing a focused refinement package.",
        "Constraints:",
        "- Keep changes scoped to listed files and subsystem.",
        "- Do not modify platform_engine.py behavior.",
        "- Do not mutate queue semantics.",
        "",
        f"Title: {title}",
        f"Objective: {objective}",
        f"Subsystem: {subsystem}",
        f"Change Type: {change_type}",
        f"Risk Level: {risk_level}",
        "",
        "Target Files:",
    ]
    lines.extend([f"- {f}" for f in target_files] or ["- (determine minimal file set)"])
    lines.append("")
    lines.append("Expected Changes:")
    for key in ("file_additions", "file_updates", "notes"):
        values = _as_list(expected_changes.get(key))
        lines.append(f"- {key}:")
        lines.extend([f"  - {v}" for v in values] or ["  - None"])
    lines.append("")
    lines.append("Validation Commands:")
    lines.extend([f"- {cmd}" for cmd in validation_commands] or ["- python -m unittest -v"])
    return {
        "prompt_id": new_id("refined_prompt"),
        "prompt_text": "\n".join(lines).strip() + "\n",
        "advisory_only": True,
        "metadata": {"advisory_only": True},
    }


def _extract_expected_changes(expected_changes: Any, files: List[str]) -> Dict[str, Any]:
    payload = dict(expected_changes) if isinstance(expected_changes, dict) else {}
    additions = [f for f in files if f in _as_list(payload.get("file_additions"))]
    updates = [f for f in files if f in _as_list(payload.get("file_updates"))]
    notes = _as_list(payload.get("notes"))
    if not additions and not updates:
        additions = [f for f in files if f.endswith(".py") or f.endswith(".md")]
        updates = [f for f in files if f not in additions]
    return {
        "file_additions": additions,
        "file_updates": updates,
        "notes": notes,
    }


def _traceability_refs(package: Dict[str, Any]) -> List[str]:
    refs = [
        str(package.get("package_id") or ""),
        str(package.get("source_batch_id") or ""),
        str((package.get("codex_prompt") or {}).get("prompt_id") or ""),
    ]
    return [r for r in refs if r]


def _risk_level_for_scope(files: List[str], commands: List[str], broad: bool) -> str:
    if broad and (len(files) > 5 or len(commands) > 4):
        return "high"
    if len(files) <= 1 and len(commands) <= 1:
        return "low"
    if len(files) <= 3 and len(commands) <= 2:
        return "medium"
    return "high"


def _estimated_scope(files: List[str], commands: List[str]) -> str:
    size = len(files) + len(commands)
    if size <= 2:
        return "tiny"
    if size <= 5:
        return "small"
    if size <= 8:
        return "medium"
    return "large"


def _build_split_summary(original_packages: Any, refined_packages: List[Dict[str, Any]]) -> Dict[str, Any]:
    original_count = len(original_packages) if isinstance(original_packages, list) else 0
    refined_count = len(refined_packages)
    broad_sources = len(
        [
            p
            for p in refined_packages
            if isinstance(p, dict) and bool((p.get("metadata") or {}).get("source_was_broad"))
        ]
    )
    high_risk = len([p for p in refined_packages if isinstance(p, dict) and p.get("risk_level") in {"high", "critical"}])
    return {
        "original_package_count": original_count,
        "refined_package_count": refined_count,
        "split_delta": refined_count - original_count,
        "refined_from_broad_count": broad_sources,
        "high_risk_refined_count": high_risk,
    }


def _as_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    out: List[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            out.append(text)
    return out


def _infer_single_or_default(values: Any, default: str) -> str:
    if isinstance(values, list) and len(values) == 1 and isinstance(values[0], str):
        return values[0]
    return default
