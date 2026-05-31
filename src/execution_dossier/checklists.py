from __future__ import annotations

from typing import Any, Dict, List


def build_review_checklist(dossier_like: Dict[str, Any]) -> List[str]:
    return [
        "Target files reviewed",
        "Validation commands verified",
        "Runtime paths unaffected",
        "Queue semantics unchanged",
        "Tests identified",
        "Rollback path documented",
    ]


def build_rollback_guidance(dossier_like: Dict[str, Any]) -> List[str]:
    files = dossier_like.get("target_files")
    file_list = [str(f) for f in files if isinstance(f, str)] if isinstance(files, list) else []
    guidance: List[str] = []
    py_files = [f for f in file_list if f.endswith(".py")]
    md_files = [f for f in file_list if f.endswith(".md")]
    if py_files:
        guidance.append("Revert added or updated test/source Python files.")
        guidance.extend([f"Revert: {f}" for f in py_files[:5]])
    if md_files:
        guidance.append("Restore previous documentation state for modified markdown files.")
        guidance.extend([f"Restore: {f}" for f in md_files[:5]])
    if not guidance:
        guidance.append("Revert file additions and restore previous state from version control history.")
    return guidance
