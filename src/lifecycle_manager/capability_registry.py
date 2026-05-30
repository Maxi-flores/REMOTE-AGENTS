from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from lifecycle_manager.capability_contracts import AgentCapabilityProfile
from lifecycle_manager.utils import new_id, utc_now


REPO_ROOT = Path(__file__).resolve().parents[2]
_CAPABILITY_CACHE: Dict[str, Dict[str, Any]] = {}


def load_agents_registry(path: str | Path = "config/registries/agents.json") -> Dict[str, Any]:
    return _load_json(REPO_ROOT / path if not Path(path).is_absolute() else Path(path))


def load_tools_registry(path: str | Path = "config/registries/tools.json") -> Dict[str, Any]:
    return _load_json(REPO_ROOT / path if not Path(path).is_absolute() else Path(path))


def load_repositories_registry(path: str | Path = "config/registries/repositories.json") -> Dict[str, Any]:
    return _load_json(REPO_ROOT / path if not Path(path).is_absolute() else Path(path))


def build_profile_for_agent_class(
    agent_class: str,
    agents_registry: Dict[str, Any],
    tools_registry: Dict[str, Any],
    repositories_registry: Dict[str, Any],
) -> Dict[str, Any]:
    agents = agents_registry.get("agents", []) if isinstance(agents_registry.get("agents"), list) else []
    repos = repositories_registry.get("repositories", []) if isinstance(repositories_registry.get("repositories"), list) else []
    tools = tools_registry.get("tools", []) if isinstance(tools_registry.get("tools"), list) else []
    agent_rec = next(
        (a for a in agents if isinstance(a, dict) and str(a.get("agent_class_id")) == agent_class),
        {},
    )
    display_name = str(agent_rec.get("display_name") or agent_class)
    role = str(agent_rec.get("role") or "Generalist")
    crew_family = agent_rec.get("crew_family") if isinstance(agent_rec.get("crew_family"), str) else None
    repositories: List[str] = []
    repository_groups: List[str] = []
    primary_roles: List[str] = []
    secondary_roles: List[str] = []
    for repo in repos:
        if not isinstance(repo, dict):
            continue
        is_primary = str(repo.get("primary_agent_class")) == agent_class
        is_twin = str(repo.get("twin_agent_class")) == agent_class
        if is_primary or is_twin:
            name = str(repo.get("name") or "").strip()
            group = str(repo.get("group") or "").strip()
            if name:
                repositories.append(name)
            if group:
                repository_groups.append(group)
            if is_primary:
                primary_roles.append(name or group or "repository")
            if is_twin:
                secondary_roles.append(name or group or "repository")
    allowed_tools = [str(t.get("name")) for t in tools if isinstance(t, dict) and isinstance(t.get("name"), str)]
    profile = AgentCapabilityProfile(
        capability_profile_id=new_id("capability_profile"),
        agent_class=agent_class,
        display_name=display_name,
        category=_infer_category(role),
        crew_family=crew_family,
        repositories=sorted(set(repositories)),
        repository_groups=sorted(set(repository_groups)),
        capabilities=[role] if role else ["Generalist support"],
        allowed_tools=sorted(set(allowed_tools)),
        denied_tools=[],
        risk_tier="medium",
        primary_roles=sorted(set(primary_roles)),
        secondary_roles=sorted(set(secondary_roles)),
        health_requirements={"min_status": "active"},
        performance_metrics={"success_rate": None, "mission_count": 0},
        status="active" if repositories else "planned",
        created_utc=utc_now(),
        updated_utc=utc_now(),
        metadata={"advisory_only": True},
    )
    return profile.to_dict()


def build_capability_profiles(
    agents_registry: Dict[str, Any] | None = None,
    tools_registry: Dict[str, Any] | None = None,
    repositories_registry: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    agents_registry = load_agents_registry() if agents_registry is None else agents_registry
    tools_registry = load_tools_registry() if tools_registry is None else tools_registry
    repositories_registry = load_repositories_registry() if repositories_registry is None else repositories_registry
    agents = agents_registry.get("agents", []) if isinstance(agents_registry.get("agents"), list) else []
    profiles: List[Dict[str, Any]] = []
    _CAPABILITY_CACHE.clear()
    for agent in agents:
        if not isinstance(agent, dict):
            continue
        agent_class = agent.get("agent_class_id")
        if not isinstance(agent_class, str) or not agent_class.strip():
            continue
        profile = build_profile_for_agent_class(agent_class, agents_registry, tools_registry, repositories_registry)
        profiles.append(profile)
        _CAPABILITY_CACHE[agent_class] = profile
    return profiles


def list_capability_profiles() -> List[Dict[str, Any]]:
    if not _CAPABILITY_CACHE:
        build_capability_profiles()
    return list(_CAPABILITY_CACHE.values())


def find_capability_profile(agent_class: str) -> Dict[str, Any] | None:
    if not _CAPABILITY_CACHE:
        build_capability_profiles()
    return _CAPABILITY_CACHE.get(agent_class)


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _infer_category(role: str) -> str:
    lowered = role.lower()
    if "security" in lowered or "auditor" in lowered:
        return "audit"
    if "diagnostic" in lowered:
        return "diagnostic"
    if "execution" in lowered or "specialist" in lowered:
        return "execution"
    return "general"
