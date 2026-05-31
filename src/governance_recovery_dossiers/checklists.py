from __future__ import annotations

from typing import Any, Dict, List


def build_review_checklist(*, action: Dict[str, Any], target_artifacts: List[str]) -> List[str]:
    title = str(action.get("title") or "governance recovery action")
    checklist = [
        f"Confirm objective scope is limited to action: {title}",
        "Confirm advisory-only mode (no auto execution, no enforcement).",
        "Confirm no edits to platform_engine.py and no .platform_queue mutation.",
        "Confirm target artifacts are inside allowed .control_plane/.config advisory paths.",
        "Confirm expected artifact updates are human-reviewed before any manual command execution.",
        "Confirm runtime queue contract remains unchanged after manual run.",
    ]
    if target_artifacts:
        checklist.append(f"Confirm all target artifacts were reviewed ({len(target_artifacts)} path(s)).")
    return checklist


def build_rollback_guidance(*, target_artifacts: List[str]) -> List[str]:
    guidance: List[str] = [
        "Rollback is artifact-only: restore previous generated advisory reports from history backups.",
        "Do not attempt runtime rollback through queue or platform engine paths.",
    ]
    for artifact in target_artifacts[:8]:
        guidance.append(f"Restore previous state for: {artifact}")
    guidance.append("If unsure, regenerate advisory artifacts with previous known-good inputs and compare diffs manually.")
    return guidance

