"""Parsers for governance markdown inputs.

These parsers are intentionally tolerant of formatting drift, but output is
strictly validated before use by the orchestrator.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.types import JSONObject


@dataclass(frozen=True, slots=True)
class RepoGuide:
    repository_name: str
    agent_class: str | None
    json_configuration: JSONObject | None
    status: str | None
    core_objective: str | None


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _coerce_json_object(raw: str) -> JSONObject | None:
    raw = raw.strip().strip("`").strip()
    if not raw:
        return None
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        last = max(raw.rfind("}"), raw.rfind("]"))
        if last < 0:
            return None
        try:
            obj = json.loads(raw[: last + 1])
        except json.JSONDecodeError:
            return None
    return obj if isinstance(obj, dict) else None


def parse_agent_guide_list(text: str) -> dict[str, RepoGuide]:
    guides: dict[str, RepoGuide] = {}

    # Split by "### RepoName" headings.
    parts = re.split(r"^###\s+", text, flags=re.MULTILINE)
    for part in parts[1:]:
        lines = part.splitlines()
        if not lines:
            continue
        repo_name = lines[0].strip()
        if not repo_name:
            continue
        body = "\n".join(lines[1:])

        agent_class = _extract_first(body, r"^\*\s+\*\*Agent Class:\*\*\s*(.+?)\s*$")
        status = _extract_first(body, r"^\*\s+\*\*Status:\*\*\s*(.+?)\s*$")
        core_objective = _extract_first(body, r"^\*\s+\*\*Core Objective:\*\*\s*(.+?)\s*$")

        json_config: JSONObject | None = None
        inline = _extract_first(body, r"^\*\s+\*\*JSON Configuration:\*\*\s*`(.+?)`\s*$")
        if inline:
            json_config = _coerce_json_object(inline)
        if json_config is None:
            fenced = _extract_json_fence(body)
            if fenced:
                json_config = _coerce_json_object(fenced)

        guides[repo_name] = RepoGuide(
            repository_name=repo_name,
            agent_class=agent_class,
            json_configuration=json_config,
            status=status,
            core_objective=core_objective,
        )

    return guides


def _extract_first(text: str, pattern: str) -> str | None:
    m = re.search(pattern, text, flags=re.MULTILINE)
    return m.group(1).strip() if m else None


def _extract_json_fence(text: str) -> str | None:
    # Match ```json ... ```
    m = re.search(r"```json\s+(.+?)\s+```", text, flags=re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else None


@dataclass(frozen=True, slots=True)
class DesignatedAgent:
    role: str
    module: str
    class_name: str


@dataclass(frozen=True, slots=True)
class DesignatedAgentsConfig:
    default_pipeline: list[str]
    agents: dict[str, DesignatedAgent]
    repository_overrides: dict[str, list[str]]


def parse_designated_agents_list(text: str) -> DesignatedAgentsConfig:
    obj = _extract_single_json_document(text)
    if obj is None:
        raise ValueError("DESIGNATED_AGENTS_LIST.md: missing JSON document")

    default_pipeline = obj.get("default_pipeline")
    agents_obj = obj.get("agents")
    overrides_obj = obj.get("repository_overrides", {})

    if not isinstance(default_pipeline, list) or not all(isinstance(x, str) for x in default_pipeline):
        raise ValueError("default_pipeline must be list[str]")
    if not isinstance(agents_obj, dict):
        raise ValueError("agents must be an object")
    if not isinstance(overrides_obj, dict):
        raise ValueError("repository_overrides must be an object")

    agents: dict[str, DesignatedAgent] = {}
    for role, spec in agents_obj.items():
        if not isinstance(role, str) or not isinstance(spec, dict):
            continue
        module = spec.get("module")
        class_name = spec.get("class")
        if not isinstance(module, str) or not isinstance(class_name, str):
            raise ValueError(f"agents.{role} must include module and class")
        agents[role] = DesignatedAgent(role=role, module=module, class_name=class_name)

    overrides: dict[str, list[str]] = {}
    for repo, pipeline in overrides_obj.items():
        if not isinstance(repo, str):
            continue
        if not isinstance(pipeline, list) or not all(isinstance(x, str) for x in pipeline):
            raise ValueError(f"repository_overrides.{repo} must be list[str]")
        overrides[repo] = pipeline

    return DesignatedAgentsConfig(
        default_pipeline=list(default_pipeline),
        agents=agents,
        repository_overrides=overrides,
    )


def _extract_single_json_document(text: str) -> JSONObject | None:
    # Prefer fenced JSON.
    fenced = _extract_json_fence(text)
    if fenced:
        return _coerce_json_object(fenced)

    # Fallback: first top-level {...} region.
    m = re.search(r"(\{.+\})", text, flags=re.DOTALL)
    return _coerce_json_object(m.group(1)) if m else None
