from __future__ import annotations

from typing import Any, Dict, List

from remediation_handoff.contracts import CodexImplementationPrompt, new_id


def build_codex_prompt_for_package(package: Dict[str, Any]) -> Dict[str, Any]:
    title = str(package.get("title") or "Implementation Package")
    objective = str(package.get("objective") or "")
    target_files = _as_list(package.get("target_files"))
    expected_changes = package.get("expected_changes") if isinstance(package.get("expected_changes"), dict) else {}
    validation_commands = _as_list(package.get("validation_commands"))
    risks = _as_list(package.get("risks"))
    review_notes = _as_list((package.get("metadata") or {}).get("human_review_notes"))

    lines: List[str] = []
    lines.append("You are implementing a deterministic advisory remediation package.")
    lines.append("Constraints:")
    lines.append("- Do not touch runtime queue semantics.")
    lines.append("- Do not modify platform_engine.py behavior.")
    lines.append("- Keep changes scoped and testable.")
    lines.append("")
    lines.append(f"Package Title: {title}")
    lines.append(f"Objective: {objective}")
    lines.append("")
    lines.append("Target Files:")
    if target_files:
        lines.extend([f"- {path}" for path in target_files])
    else:
        lines.append("- (determine minimal file set)")
    lines.append("")
    lines.append("Expected Changes:")
    additions = _as_list(expected_changes.get("file_additions"))
    updates = _as_list(expected_changes.get("file_updates"))
    notes = _as_list(expected_changes.get("notes"))
    lines.append("- File additions:")
    lines.extend([f"  - {item}" for item in additions] or ["  - None"])
    lines.append("- File updates:")
    lines.extend([f"  - {item}" for item in updates] or ["  - None"])
    if notes:
        lines.append("- Notes:")
        lines.extend([f"  - {item}" for item in notes])
    lines.append("")
    lines.append("Validation Commands:")
    lines.extend([f"- {command}" for command in validation_commands] or ["- python -m unittest -v"])
    lines.append("")
    lines.append("Risks:")
    lines.extend([f"- {risk}" for risk in risks] or ["- Low"])
    if review_notes:
        lines.append("")
        lines.append("Human Review Notes:")
        lines.extend([f"- {note}" for note in review_notes])

    prompt = CodexImplementationPrompt(
        prompt_id=new_id("codex_prompt"),
        package_id=str(package.get("package_id") or ""),
        prompt_text="\n".join(lines).strip() + "\n",
        advisory_only=True,
        metadata={"advisory_only": True},
    )
    return prompt.to_dict()


def _as_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    out: List[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            out.append(text)
    return out
