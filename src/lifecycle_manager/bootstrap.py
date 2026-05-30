from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Set

from lifecycle_manager.capability_contracts import validate_capability_profile_dict
from lifecycle_manager.capability_registry import (
    build_capability_profiles,
    load_agents_registry,
    load_repositories_registry,
    load_tools_registry,
)
from lifecycle_manager.lifecycle_contracts import validate_lifecycle_state_dict
from lifecycle_manager.store import LifecycleStore
from lifecycle_manager.utils import utc_now


def seed_lifecycle_capabilities(base_dir: str | Path = ".") -> Dict[str, Any]:
    root = Path(base_dir)
    store = LifecycleStore(path=root / ".lifecycle" / "agents.json")
    state = store.load_state()
    profiles_state = state.get("capability_profiles")
    if not isinstance(profiles_state, dict):
        profiles_state = {}
        state["capability_profiles"] = profiles_state
    lifecycle_state = state.get("lifecycle_states")
    if not isinstance(lifecycle_state, dict):
        lifecycle_state = {}
        state["lifecycle_states"] = lifecycle_state
    events = state.get("events")
    if not isinstance(events, list):
        events = []
        state["events"] = events

    agents_registry = load_agents_registry(root / "config" / "registries" / "agents.json")
    tools_registry = load_tools_registry(root / "config" / "registries" / "tools.json")
    repositories_registry = load_repositories_registry(root / "config" / "registries" / "repositories.json")
    legacy_registry = _load_json(root / "config" / "agent_registry.json")

    repository_by_agent = _collect_repository_assignments(legacy_registry)
    active_agent_classes = _collect_active_agent_classes(legacy_registry, agents_registry)

    built_profiles = build_capability_profiles(
        agents_registry=agents_registry,
        tools_registry=tools_registry,
        repositories_registry=repositories_registry,
    )
    built_by_agent = {
        str(profile.get("agent_class")): profile
        for profile in built_profiles
        if isinstance(profile, dict) and isinstance(profile.get("agent_class"), str)
    }
    agents_meta = _agent_metadata(agents_registry)
    now = utc_now()

    added_profiles = 0
    added_lifecycle_states = 0

    for agent_class in sorted(active_agent_classes):
        if agent_class not in profiles_state:
            profile = dict(built_by_agent.get(agent_class) or _fallback_profile(agent_class, agents_meta.get(agent_class, {}), now))
            repos = list(profile.get("repositories") or [])
            legacy_repos = sorted(repository_by_agent.get(agent_class, set()))
            if legacy_repos:
                repos = sorted(set(str(r) for r in repos + legacy_repos if str(r).strip()))
            profile["repositories"] = repos
            profile["status"] = "active" if repos else str(profile.get("status") or "planned")
            profile["updated_utc"] = now
            profile["metadata"] = {
                **(profile.get("metadata") if isinstance(profile.get("metadata"), dict) else {}),
                "seeded_by": "lifecycle.bootstrap",
                "seed_sources": [
                    "config/registries/agents.json",
                    "config/agent_registry.json",
                    "AGENT_GUIDE_LIST.md",
                    "DESIGNATED_AGENTS_LIST.md",
                ],
                "advisory_only": True,
            }
            validate_capability_profile_dict(profile)
            profiles_state[agent_class] = profile
            added_profiles += 1

        agent_id = f"agent::{agent_class}"
        if agent_id not in lifecycle_state:
            assigned_repositories = sorted(repository_by_agent.get(agent_class, set()))
            lifecycle = {
                "agent_id": agent_id,
                "agent_class": agent_class,
                "version": "v1",
                "status": "active" if assigned_repositories else "planned",
                "health": "healthy" if assigned_repositories else "unknown",
                "availability": "available" if assigned_repositories else "paused",
                "last_seen_utc": now if assigned_repositories else None,
                "assigned_repositories": assigned_repositories,
                "current_missions": [],
                "performance_summary": {
                    "missions_completed": 0,
                    "success_rate": None,
                },
                "lifecycle_notes": [
                    "Seeded from lifecycle bootstrap using canonical and legacy registries.",
                ],
                "created_utc": now,
                "updated_utc": now,
                "metadata": {
                    "seeded_by": "lifecycle.bootstrap",
                    "advisory_only": True,
                },
            }
            validate_lifecycle_state_dict(lifecycle)
            lifecycle_state[agent_id] = lifecycle
            added_lifecycle_states += 1

    events.append(
        {
            "event_type": "lifecycle_seed",
            "created_utc": now,
            "added_profiles": added_profiles,
            "added_lifecycle_states": added_lifecycle_states,
            "active_agent_classes": len(active_agent_classes),
            "advisory_only": True,
        }
    )
    store.save_state(state)
    return {
        "path": str(store.path),
        "added_profiles": added_profiles,
        "added_lifecycle_states": added_lifecycle_states,
        "capability_profiles_total": len(profiles_state),
        "lifecycle_states_total": len(lifecycle_state),
        "advisory_only": True,
    }


def _collect_active_agent_classes(legacy_registry: Dict[str, Any], agents_registry: Dict[str, Any]) -> Set[str]:
    active: Set[str] = set()
    default_profile = legacy_registry.get("default_profile")
    if isinstance(default_profile, dict):
        for key in ("primary_agent_class", "twin_agent_class"):
            value = default_profile.get(key)
            if isinstance(value, str) and value.strip():
                active.add(value.strip())
    repositories = legacy_registry.get("repositories")
    if isinstance(repositories, dict):
        for route in repositories.values():
            if not isinstance(route, dict):
                continue
            for key in ("primary_agent_class", "twin_agent_class"):
                value = route.get(key)
                if isinstance(value, str) and value.strip():
                    active.add(value.strip())
    if active:
        return active
    agents = agents_registry.get("agents")
    if isinstance(agents, list):
        for agent in agents:
            if isinstance(agent, dict):
                value = agent.get("agent_class_id")
                if isinstance(value, str) and value.strip():
                    active.add(value.strip())
    return active


def _collect_repository_assignments(legacy_registry: Dict[str, Any]) -> Dict[str, Set[str]]:
    assignments: Dict[str, Set[str]] = {}
    repositories = legacy_registry.get("repositories")
    if not isinstance(repositories, dict):
        return assignments
    for repository_name, route in repositories.items():
        if not isinstance(route, dict):
            continue
        for key in ("primary_agent_class", "twin_agent_class"):
            agent_class = route.get(key)
            if not isinstance(agent_class, str) or not agent_class.strip():
                continue
            assignments.setdefault(agent_class.strip(), set()).add(str(repository_name))
    return assignments


def _agent_metadata(agents_registry: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    metadata: Dict[str, Dict[str, Any]] = {}
    agents = agents_registry.get("agents")
    if not isinstance(agents, list):
        return metadata
    for agent in agents:
        if not isinstance(agent, dict):
            continue
        key = agent.get("agent_class_id")
        if isinstance(key, str) and key.strip():
            metadata[key.strip()] = dict(agent)
    return metadata


def _fallback_profile(agent_class: str, metadata: Dict[str, Any], now: str) -> Dict[str, Any]:
    display_name = str(metadata.get("display_name") or agent_class)
    role = str(metadata.get("role") or "Advisory autonomous component")
    crew = metadata.get("crew_family")
    crew_family = str(crew) if isinstance(crew, str) and crew.strip() else None
    return {
        "capability_profile_id": f"capability_profile::{agent_class}",
        "agent_class": agent_class,
        "display_name": display_name,
        "category": "general",
        "crew_family": crew_family,
        "repositories": [],
        "repository_groups": [],
        "capabilities": [role],
        "allowed_tools": [],
        "denied_tools": [],
        "risk_tier": "medium",
        "primary_roles": [],
        "secondary_roles": [],
        "health_requirements": {"min_status": "active"},
        "performance_metrics": {"missions_completed": 0, "success_rate": None},
        "status": "planned",
        "created_utc": now,
        "updated_utc": now,
        "metadata": {"advisory_only": True},
    }


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}

