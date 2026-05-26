#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parent


def _normalize_repo_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _infer_repo_from_github_url(url: str) -> str | None:
    url = url.strip().strip("`")
    if not url or url.lower() in {"none", "none listed"}:
        return None
    m = re.match(r"^https?://github\.com/[^/]+/([^/]+?)(?:\.git)?/?$", url)
    if not m:
        return None
    return m.group(1)


def _canonical_repo_name(project: str, remote_url: str | None) -> str:
    project = project.strip()

    # Inventory lists nested Dealinstinct repos separately; class/json definitions are repo-wide.
    if project.lower().startswith("dealinstinct"):
        return "Dealinstinct"

    if _normalize_repo_key(project) in {_normalize_repo_key("Sapient KB")}:
        return "Sapient-KB"

    if _normalize_repo_key(project) in {_normalize_repo_key("Trade Agent – V1"), _normalize_repo_key("Trade-Agent-V1")}:
        return "Trade-Agent-V1"

    if remote_url:
        inferred = _infer_repo_from_github_url(remote_url)
        if inferred:
            return inferred

    return project


def _iter_section_lines(text: str, heading: str) -> Iterable[str]:
    lines = text.splitlines()
    start_idx = None
    heading_re = re.compile(rf"^\s*{re.escape(heading)}\s*$")
    next_heading_re = re.compile(r"^\s*##\s+")

    for i, line in enumerate(lines):
        if heading_re.match(line):
            start_idx = i + 1
            break

    if start_idx is None:
        return []

    section: list[str] = []
    for line in lines[start_idx:]:
        if next_heading_re.match(line):
            break
        section.append(line)
    return section


def _parse_markdown_table(section_lines: Iterable[str]) -> list[list[str]]:
    rows: list[list[str]] = []
    for raw in section_lines:
        line = raw.strip()
        if not line.startswith("|"):
            continue
        if re.match(r"^\|\s*-{3,}\s*\|", line):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        if cells[0].lower() in {"project", "---"}:
            continue
        rows.append(cells)
    return rows


@dataclass(frozen=True)
class InventoryRepo:
    repository_name: str
    remote_url: str | None
    classification: str | None
    source: str


def parse_repo_inventory(path: Path) -> list[InventoryRepo]:
    text = path.read_text(encoding="utf-8", errors="replace")

    repos: list[InventoryRepo] = []

    active_section = _iter_section_lines(text, "## Active Local Git Repos")
    for row in _parse_markdown_table(active_section):
        # | Project | Local path | Remote URL | Has `.git` | Classification | Recommended next action |
        project = row[0]
        remote_url = row[2] if len(row) > 2 else None
        classification = row[4] if len(row) > 4 else None
        repos.append(
            InventoryRepo(
                repository_name=project.strip(),
                remote_url=(remote_url.strip() if remote_url else None),
                classification=(classification.strip() if classification else None),
                source="Active Local Git Repos",
            )
        )

    mapped_section = _iter_section_lines(text, "## Local Folders Without Git But Mapped To GitHub")
    for row in _parse_markdown_table(mapped_section):
        project = row[0]
        remote_url = row[2] if len(row) > 2 else None
        classification = row[4] if len(row) > 4 else None
        repos.append(
            InventoryRepo(
                repository_name=project.strip(),
                remote_url=(remote_url.strip() if remote_url else None),
                classification=(classification.strip() if classification else None),
                source="Local Folders Without Git But Mapped To GitHub",
            )
        )

    # Some repo targets exist only in the "Production order" section as a single-column pipe list.
    production_section = _iter_section_lines(text, "## Production order:")
    for raw in production_section:
        line = raw.strip()
        m = re.match(r"^\|\s*([^\|]+?)\s*\|\s*$", line)
        if not m:
            continue
        name = m.group(1).strip().strip("`")
        if name:
            repos.append(
                InventoryRepo(
                    repository_name=name,
                    remote_url=None,
                    classification="production-order-target",
                    source="Production order",
                )
            )

    # De-duplicate by displayed repository name while preserving order.
    seen: set[str] = set()
    deduped: list[InventoryRepo] = []
    for repo in repos:
        key = repo.repository_name.strip()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(repo)
    return deduped


@dataclass(frozen=True)
class ClassAssignment:
    target_repo: str
    primary_class: str | None
    twin_context_class: str | None


def parse_class_list(path: Path) -> dict[str, ClassAssignment]:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    repo_to_assignment: dict[str, ClassAssignment] = {}

    current_repo: str | None = None
    primary: str | None = None
    twin: str | None = None

    def _strip_repo_annotation(repo: str) -> str:
        # PF_CLASS_LIST commonly annotates repos as "Name (context)"; inventory/JSON use the bare name.
        return re.sub(r"\s*\(.*?\)\s*$", "", repo).strip()

    def flush() -> None:
        nonlocal current_repo, primary, twin
        if current_repo:
            normalized_repo = _strip_repo_annotation(current_repo)
            assignment = ClassAssignment(
                target_repo=normalized_repo,
                primary_class=(primary.strip() if primary else None),
                twin_context_class=(twin.strip() if twin else None),
            )
            repo_to_assignment[_normalize_repo_key(normalized_repo)] = assignment
        current_repo = None
        primary = None
        twin = None

    target_re = re.compile(r"^\s*-\s*Target Repo:\s*(.+?)\s*$", re.IGNORECASE)
    primary_re = re.compile(r"^\s*-\s*Primary Class:\s*(.+?)\s*$", re.IGNORECASE)
    twin_re = re.compile(r"^\s*-\s*Context Twin Class:\s*(.+?)\s*$", re.IGNORECASE)

    for line in lines:
        m = target_re.match(line)
        if m:
            flush()
            current_repo = m.group(1)
            continue
        m = primary_re.match(line)
        if m and current_repo:
            primary = m.group(1)
            continue
        m = twin_re.match(line)
        if m and current_repo:
            twin = m.group(1)
            continue

    flush()
    return repo_to_assignment


def _extract_json_code_blocks(text: str) -> list[str]:
    blocks: list[str] = []
    pos = 0
    lower = text.lower()
    while True:
        start = lower.find("```json", pos)
        if start < 0:
            break
        start_line_end = text.find("\n", start)
        if start_line_end < 0:
            break
        end = text.find("```", start_line_end + 1)
        if end < 0:
            break
        blocks.append(text[start_line_end + 1 : end].strip())
        pos = end + 3
    return blocks


def _coerce_json_object(raw: str) -> Any | None:
    raw = raw.strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Best-effort salvage: trim to last closing brace/bracket.
        last_curly = raw.rfind("}")
        last_square = raw.rfind("]")
        last = max(last_curly, last_square)
        if last <= 0:
            return None
        try:
            return json.loads(raw[: last + 1])
        except json.JSONDecodeError:
            return None


def parse_json_list(path: Path) -> dict[str, dict[str, Any]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    blocks = _extract_json_code_blocks(text)

    repo_to_json: dict[str, dict[str, Any]] = {}
    for block in blocks:
        obj = _coerce_json_object(block)
        if not isinstance(obj, dict):
            continue
        repo_name = obj.get("repository_name")
        if not isinstance(repo_name, str) or not repo_name.strip():
            continue
        repo_to_json[_normalize_repo_key(repo_name)] = obj
    return repo_to_json


@dataclass(frozen=True)
class MappedAgent:
    display_repo_name: str
    canonical_repo_name: str
    agent_class: str
    json_repository_name: str | None
    json_configuration: str | None
    status: str
    core_objective: str


def _compact_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def correlate(
    inventory: list[InventoryRepo],
    class_map: dict[str, ClassAssignment],
    json_map: dict[str, dict[str, Any]],
) -> list[MappedAgent]:
    mapped: list[MappedAgent] = []
    for repo in inventory:
        canonical = _canonical_repo_name(repo.repository_name, repo.remote_url)
        key = _normalize_repo_key(canonical)

        class_assignment = class_map.get(key)
        json_obj = json_map.get(key)
        json_str = _compact_json(json_obj) if json_obj else None
        json_repo_name = json_obj.get("repository_name") if isinstance(json_obj, dict) else None
        if not isinstance(json_repo_name, str):
            json_repo_name = None

        if class_assignment and json_obj:
            status = "Ready for Training"
        elif not class_assignment and json_obj:
            status = "Missing Class"
        elif class_assignment and not json_obj:
            status = "Pending Implementation"
        else:
            status = "Pending Definition/Training"

        if class_assignment:
            primary = class_assignment.primary_class or "Unknown Primary Class"
            twin = class_assignment.twin_context_class or "Unknown Context Twin Class"
            agent_class = f"Primary: {primary}; Twin: {twin}"
            core_objective = (
                f"Govern {canonical} by executing {primary} tasks with {twin} validation to prevent regressions and secret leaks."
            )
        elif json_obj and isinstance(json_obj.get("recommended_agent_assignment"), dict):
            rec = json_obj["recommended_agent_assignment"]
            primary = rec.get("primary_class") or "Unknown Primary Class"
            twin = rec.get("twin_context_class") or "Unknown Context Twin Class"
            agent_class = f"Primary: {primary}; Twin: {twin}"
            core_objective = (
                f"Govern {canonical} by executing {primary} tasks with {twin} validation to prevent regressions and secret leaks."
            )
        else:
            agent_class = "Pending Definition/Training"
            core_objective = (
                f"Define an agent class and JSON configuration for {canonical} based on its functional scope and governance needs."
            )

        mapped.append(
            MappedAgent(
                display_repo_name=repo.repository_name,
                canonical_repo_name=canonical,
                agent_class=agent_class,
                json_repository_name=json_repo_name,
                json_configuration=json_str,
                status=status,
                core_objective=core_objective,
            )
        )
    return mapped


def render_markdown(mapped: list[MappedAgent]) -> str:
    total = len(mapped)
    ready = sum(1 for m in mapped if m.status == "Ready for Training")
    pending = total - ready

    lines: list[str] = []
    lines.append("# Agent Guidance & Implementation Directory (AGENT_GUIDE_LIST.md)")
    lines.append("")
    lines.append("## 1. System Overview")
    lines.append(
        f"{total} repositories are mapped to required agent roles; {ready} have both class and JSON definitions and are ready for training."
    )
    lines.append(
        f"{pending} are pending definition/training due to missing class and/or JSON configuration references."
    )
    lines.append("")
    lines.append("## 2. Agent Mapping by Repository")

    for item in mapped:
        lines.append("")
        lines.append(f"### {item.display_repo_name}")
        lines.append(f"* **Agent Class:** {item.agent_class}")
        lines.append(f"* **JSON Configuration:** `{item.json_configuration or 'N/A'}`")
        lines.append(f"* **Status:** {item.status}")
        lines.append(f"* **Core Objective:** {item.core_objective}")

    lines.append("")
    lines.append("## 3. Training & Implementation Matrix")
    lines.append("")
    lines.append("| Agent Class | Target Repository | Training Data (JSON Ref) | Implementation Status |")
    lines.append("| :--- | :--- | :--- | :--- |")
    for item in mapped:
        json_ref = "N/A"
        if item.json_repository_name:
            json_ref = f"`repository_name={item.json_repository_name}`"
        lines.append(
            f"| {item.agent_class} | {item.display_repo_name} | {json_ref} | {item.status} |"
        )
    lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def _resolve_input_path(candidate: str) -> Path:
    p = Path(candidate)
    if p.is_absolute() and p.exists():
        return p
    rel = (REPO_ROOT / candidate)
    if rel.exists():
        return rel
    # Problem statement uses *.md; support both.
    if not candidate.endswith(".md"):
        md_rel = (REPO_ROOT / f"{candidate}.md")
        if md_rel.exists():
            return md_rel
    else:
        non_md = (REPO_ROOT / candidate[:-3])
        if non_md.exists():
            return non_md
    raise FileNotFoundError(f"Could not find input file: {candidate}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate AGENT_GUIDE_LIST.md by correlating repo inventory, class list, and JSON manifests."
    )
    parser.add_argument("--inventory", default="PF_REPO_INVENTORY_LIST")
    parser.add_argument("--classes", default="PF_CLASS_LIST")
    parser.add_argument("--json", dest="json_list", default="PF_JSON_LIST")
    parser.add_argument("--out", default="AGENT_GUIDE_LIST.md")
    args = parser.parse_args()

    inventory_path = _resolve_input_path(args.inventory)
    classes_path = _resolve_input_path(args.classes)
    json_path = _resolve_input_path(args.json_list)
    out_path = (REPO_ROOT / args.out) if not Path(args.out).is_absolute() else Path(args.out)

    inventory = parse_repo_inventory(inventory_path)
    class_map = parse_class_list(classes_path)
    json_map = parse_json_list(json_path)
    mapped = correlate(inventory, class_map, json_map)

    out_path.write_text(render_markdown(mapped), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
