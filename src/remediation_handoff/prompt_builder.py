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
    metadata = package.get("metadata") if isinstance(package.get("metadata"), dict) else {}
    review_notes = _as_list(metadata.get("human_review_notes"))
    target_repository = _target_repository_name(package, metadata)
    primary_agent_class, max_context_chars = _execution_bounds_for_repository(target_repository)

    lines: List[str] = []
    lines.append(
        "You are an autonomous, high-fidelity UI/UX Code Compiler operating within the strict bounds of the REMOTE-AGENTS Architecture."
    )
    lines.append("Your single output is raw, production-ready frontend code matching the active governance registry contract.")
    lines.append("")
    lines.append("ABSOLUTE COMPILER RUNTIME CONTRACT (STRICT):")
    lines.append("- RAW-SOURCE-ONLY OUTPUT: emit only raw source payload. No code fences.")
    lines.append("- NO CONVERSATIONAL NOISE: no greetings, explanations, markdown, or bullets in emitted artifact.")
    lines.append("- DESIGN GENOME ADHERENCE: follow active skills.md tokens; no inline style overrides/hardcoded style tokens.")
    lines.append("- BUG BOUNDARY ISOLATION: isolate component boundaries before repair; preserve responsive fluid scaling.")
    lines.append("- EMIT SINGLE ARTIFACT: return one fully refactored source payload.")
    lines.append("")
    lines.append("EXECUTION BOUNDS:")
    lines.append(f"- target_repository={target_repository}")
    lines.append(f"- primary_agent_class={primary_agent_class}")
    lines.append(f"- max_context_chars={max_context_chars}")
    lines.append("- constraints_source=governance_registry")
    lines.append("")
    lines.append("Repository safety constraints:")
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
    lines.append("")
    lines.append("INPUT TARGET REPOSITORY NAME, SKILLS.MD TOKENS, AND SOURCE CODE TO REFACTOR BELOW")

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


def _target_repository_name(package: Dict[str, Any], metadata: Dict[str, Any]) -> str:
    raw = package.get("target_repository")
    if not isinstance(raw, str) or not raw.strip():
        raw = metadata.get("repository")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return "unknown"


def _execution_bounds_for_repository(repository_name: str) -> tuple[str, int]:
    if repository_name in {"ConceptSHOP", "Powerframe-CRM", "TheRocketTree-Web"}:
        return "ViteReactPrimaryAgent", 12000
    if repository_name in {"Dealinstinct Frontend", "Dealinstinct V2", "Bikerinstinct", "WOMmedia"}:
        return "NextJsPrimaryAgent", 12000
    if repository_name == "Mucho3D":
        return "3DSceneOrchestratorAgent", 16000
    return "RuntimeDiagnosticAgent", 12000
