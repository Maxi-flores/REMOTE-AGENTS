#!/usr/bin/env python3
import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent


def _normalize_repo_key(value):
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


def _strip_parens_suffix(value):
    return re.sub(r"\s*\(.*?\)\s*$", "", (value or "")).strip()


def _infer_repo_from_github_url(url):
    url = (url or "").strip().strip("`")
    if not url or url.lower() in {"none", "none listed"}:
        return None
    m = re.match(r"^https?://github\.com/[^/]+/([^/]+?)(?:\.git)?/?$", url)
    return m.group(1) if m else None


def _canonical_repo_name(project, remote_url):
    project = (project or "").strip()

    # Inventory lists nested Dealinstinct repos separately; class/json definitions are repo-wide.
    if project.lower().startswith("dealinstinct"):
        return "Dealinstinct"

    if _normalize_repo_key(project) == _normalize_repo_key("Sapient KB"):
        return "Sapient-KB"

    if _normalize_repo_key(project) in {
        _normalize_repo_key("Trade Agent – V1"),
        _normalize_repo_key("Trade Agent - V1"),
        _normalize_repo_key("Trade-Agent-V1"),
    }:
        return "Trade-Agent-V1"

    inferred = _infer_repo_from_github_url(remote_url) if remote_url else None
    return inferred or project


def _iter_section_lines(text, heading):
    lines = (text or "").splitlines()
    start_idx = None
    heading_re = re.compile(r"^\s*" + re.escape(heading) + r"\s*$")
    next_heading_re = re.compile(r"^\s*##\s+")

    for i, line in enumerate(lines):
        if heading_re.match(line):
            start_idx = i + 1
            break

    if start_idx is None:
        return []

    section = []
    for line in lines[start_idx:]:
        if next_heading_re.match(line):
            break
        section.append(line)
    return section


def _parse_markdown_table(section_lines):
    rows = []
    for raw in section_lines or []:
        line = (raw or "").strip()
        if not line.startswith("|"):
            continue
        if re.match(r"^\|\s*-{3,}\s*\|", line):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        if (cells[0] or "").strip().lower() in {"project", "---"}:
            continue
        rows.append(cells)
    return rows


def parse_repo_inventory(path):
    text = Path(path).read_text(encoding="utf-8", errors="replace")

    repos = []

    active_section = _iter_section_lines(text, "## Active Local Git Repos")
    for row in _parse_markdown_table(active_section):
        # | Project | Local path | Remote URL | Has `.git` | Classification | Recommended next action |
        project = (row[0] if len(row) > 0 else "").strip()
        remote_url = (row[2] if len(row) > 2 else "").strip() or None
        classification = (row[4] if len(row) > 4 else "").strip() or None
        repos.append(
            {
                "repository_name": project,
                "remote_url": remote_url,
                "classification": classification,
                "source": "Active Local Git Repos",
            }
        )

    mapped_section = _iter_section_lines(text, "## Local Folders Without Git But Mapped To GitHub")
    for row in _parse_markdown_table(mapped_section):
        project = (row[0] if len(row) > 0 else "").strip()
        remote_url = (row[2] if len(row) > 2 else "").strip() or None
        classification = (row[4] if len(row) > 4 else "").strip() or None
        repos.append(
            {
                "repository_name": project,
                "remote_url": remote_url,
                "classification": classification,
                "source": "Local Folders Without Git But Mapped To GitHub",
            }
        )

    # Some repo targets exist only in the "Production order" section as a single-column pipe list.
    production_section = _iter_section_lines(text, "## Production order:")
    for raw in production_section:
        line = (raw or "").strip()
        m = re.match(r"^\|\s*([^\|]+?)\s*\|\s*$", line)
        if not m:
            continue
        name = m.group(1).strip().strip("`")
        if name:
            repos.append(
                {
                    "repository_name": name,
                    "remote_url": None,
                    "classification": "production-order-target",
                    "source": "Production order",
                }
            )

    # De-duplicate by displayed repository name while preserving order.
    seen = set()
    deduped = []
    for repo in repos:
        key = (repo.get("repository_name") or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(repo)
    return deduped


def parse_class_list(path):
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()

    repo_to_assignment = {}

    current_repo = None
    primary = None
    twin = None

    def flush():
        nonlocal current_repo, primary, twin
        if current_repo:
            normalized_repo = _strip_parens_suffix(current_repo)
            repo_to_assignment[_normalize_repo_key(normalized_repo)] = {
                "target_repo": normalized_repo,
                "primary_class": (primary.strip() if primary else None),
                "twin_context_class": (twin.strip() if twin else None),
            }
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
            current_repo = m.group(1).strip()
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


def _extract_json_code_blocks(text):
    blocks = []
    for m in re.finditer(r"```json\s*(.*?)```", text or "", flags=re.IGNORECASE | re.DOTALL):
        raw = (m.group(1) or "").strip()
        if raw:
            blocks.append(raw)
    return blocks


def _coerce_json_object(raw):
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Best-effort salvage: trim to last closing brace.
        last_curly = raw.rfind("}")
        if last_curly <= 0:
            return None
        try:
            return json.loads(raw[: last_curly + 1])
        except json.JSONDecodeError:
            return None


def _compact_json(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def parse_json_list(path):
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    blocks = _extract_json_code_blocks(text)

    repo_to_json = {}
    for block in blocks:
        obj = _coerce_json_object(block)
        if not isinstance(obj, dict):
            continue
        repo_name = obj.get("repository_name")
        if not isinstance(repo_name, str) or not repo_name.strip():
            continue
        repo_to_json[_normalize_repo_key(repo_name)] = obj
    return repo_to_json


def correlate(inventory, class_map, json_map):
    mapped = []

    for repo in inventory or []:
        display = (repo.get("repository_name") or "").strip()
        remote_url = repo.get("remote_url")
        canonical = _canonical_repo_name(display, remote_url)
        key = _normalize_repo_key(canonical)

        class_assignment = class_map.get(key)
        json_obj = json_map.get(key)

        if class_assignment and json_obj:
            status = "Ready for Training"
        elif (not class_assignment) and json_obj:
            status = "Missing Class"
        elif class_assignment and (not json_obj):
            status = "Pending Implementation"
        else:
            status = "Pending Definition/Training"

        agent_class = None
        primary = None
        twin = None

        if class_assignment:
            primary = class_assignment.get("primary_class") or "Unknown Primary Class"
            twin = class_assignment.get("twin_context_class") or "Unknown Context Twin Class"
            agent_class = "Primary: " + primary + "; Twin: " + twin
        elif json_obj and isinstance(json_obj.get("recommended_agent_assignment"), dict):
            rec = json_obj.get("recommended_agent_assignment") or {}
            primary = rec.get("primary_class") or "Unknown Primary Class"
            twin = rec.get("twin_context_class") or "Unknown Context Twin Class"
            agent_class = "Primary: " + primary + "; Twin: " + twin
        else:
            agent_class = "Pending Definition/Training"

        if primary and twin:
            core_objective = (
                "Govern "
                + canonical
                + " by executing "
                + primary
                + " tasks with "
                + twin
                + " validation to prevent regressions and secret leaks."
            )
        else:
            core_objective = (
                "Define an agent class and JSON configuration for "
                + canonical
                + " based on its functional scope and governance needs."
            )

        json_repo_name = None
        json_compact = None
        if isinstance(json_obj, dict):
            json_repo_name = json_obj.get("repository_name") if isinstance(json_obj.get("repository_name"), str) else None
            json_compact = _compact_json(json_obj)

        mapped.append(
            {
                "display_repo_name": display,
                "canonical_repo_name": canonical,
                "agent_class": agent_class,
                "json_repository_name": json_repo_name,
                "json_configuration": json_compact,
                "status": status,
                "core_objective": core_objective,
            }
        )

    return mapped


def render_markdown(mapped):
    total = len(mapped or [])
    ready = sum(1 for m in mapped or [] if m.get("status") == "Ready for Training")
    pending = total - ready

    missing_class = sum(1 for m in mapped or [] if m.get("status") == "Missing Class")
    pending_impl = sum(1 for m in mapped or [] if m.get("status") == "Pending Implementation")
    pending_def = sum(1 for m in mapped or [] if m.get("status") == "Pending Definition/Training")

    lines = []
    lines.append("# Agent Guidance & Implementation Directory (AGENT_GUIDE_LIST.md)")
    lines.append("")
    lines.append("## 1. System Overview")
    lines.append(
        str(total)
        + " agent targets are tracked; "
        + str(ready)
        + " are Ready for Training and "
        + str(pending)
        + " are Pending."
    )
    lines.append(
        "Pending breakdown: "
        + str(missing_class)
        + " Missing Class; "
        + str(pending_impl)
        + " Pending Implementation; "
        + str(pending_def)
        + " Pending Definition/Training."
    )
    lines.append("")
    lines.append("## 2. Agent Mapping by Repository")

    for item in mapped or []:
        lines.append("")
        lines.append("### " + (item.get("display_repo_name") or item.get("canonical_repo_name") or "Unknown"))
        lines.append("* **Agent Class:** " + (item.get("agent_class") or "Pending Definition/Training"))
        lines.append("* **JSON Configuration:** `" + (item.get("json_configuration") or "N/A") + "`")
        lines.append("* **Status:** " + (item.get("status") or "Pending Definition/Training"))
        lines.append("* **Core Objective:** " + (item.get("core_objective") or ""))

    lines.append("")
    lines.append("## 3. Training & Implementation Matrix")
    lines.append("")
    lines.append("| Agent Class | Target Repository | Training Data (JSON Ref) | Implementation Status |")
    lines.append("| :--- | :--- | :--- | :--- |")

    for item in mapped or []:
        json_ref = "N/A"
        if item.get("json_repository_name"):
            json_ref = "`repository_name=" + item.get("json_repository_name") + "`"
        lines.append(
            "| "
            + (item.get("agent_class") or "Pending Definition/Training")
            + " | "
            + (item.get("display_repo_name") or item.get("canonical_repo_name") or "Unknown")
            + " | "
            + json_ref
            + " | "
            + (item.get("status") or "Pending Definition/Training")
            + " |"
        )

    lines.append("")
    return "\n".join(lines) + "\n"


def _resolve_input_path(candidate):
    candidate = (candidate or "").strip()
    if not candidate:
        raise FileNotFoundError("Missing input file name")

    p = Path(candidate)
    if p.is_absolute() and p.exists():
        return p

    rel = REPO_ROOT / candidate
    if rel.exists():
        return rel

    # Problem statement uses *.md; repo uses no extension. Support both.
    if not candidate.lower().endswith(".md"):
        md_rel = REPO_ROOT / (candidate + ".md")
        if md_rel.exists():
            return md_rel
    else:
        non_md = REPO_ROOT / candidate[:-3]
        if non_md.exists():
            return non_md

    raise FileNotFoundError("Could not find input file: " + candidate)


def main():
    inventory_path = _resolve_input_path("PF_REPO_INVENTORY_LIST")
    classes_path = _resolve_input_path("PF_CLASS_LIST")
    json_path = _resolve_input_path("PF_JSON_LIST")
    out_path = REPO_ROOT / "AGENT_GUIDE_LIST.md"

    inventory = parse_repo_inventory(inventory_path)
    class_map = parse_class_list(classes_path)
    json_map = parse_json_list(json_path)
    mapped = correlate(inventory, class_map, json_map)

    out_path.write_text(render_markdown(mapped), encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("ERROR:", str(exc))
        raise SystemExit(1)
