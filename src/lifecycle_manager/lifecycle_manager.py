from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from lifecycle_manager.lifecycle_contracts import AgentLifecycleState
from lifecycle_manager.store import LifecycleStore
from lifecycle_manager.utils import new_id, utc_now


def create_lifecycle_state(agent_class: str, version: str = "v1", status: str = "registered") -> Dict[str, Any]:
    now = utc_now()
    state = AgentLifecycleState(
        agent_id=new_id("agent"),
        agent_class=agent_class,
        version=version,
        status=status,
        health="unknown",
        availability="available",
        last_seen_utc=None,
        assigned_repositories=[],
        current_missions=[],
        performance_summary={"mission_count": 0, "success_rate": None},
        lifecycle_notes=[],
        created_utc=now,
        updated_utc=now,
        metadata={"advisory_only": True},
    )
    return state.to_dict()


def register_agent(store: LifecycleStore, agent_class: str, version: str = "v1", status: str = "registered") -> Dict[str, Any]:
    state = create_lifecycle_state(agent_class=agent_class, version=version, status=status)
    store.register_agent(state)
    return state


def summarize_agent(agent_state: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "agent_id": agent_state.get("agent_id"),
        "agent_class": agent_state.get("agent_class"),
        "status": agent_state.get("status"),
        "health": agent_state.get("health"),
        "availability": agent_state.get("availability"),
        "assigned_repository_count": len(agent_state.get("assigned_repositories", []))
        if isinstance(agent_state.get("assigned_repositories"), list)
        else 0,
    }


def summarize_repository_agents(
    repository_name: str,
    lifecycle_states: List[Dict[str, Any]],
    capability_profiles: List[Dict[str, Any]],
) -> Dict[str, Any]:
    covered_by = [
        profile.get("agent_class")
        for profile in capability_profiles
        if isinstance(profile, dict)
        and isinstance(profile.get("repositories"), list)
        and repository_name in profile.get("repositories", [])
    ]
    active_agents = [
        state.get("agent_id")
        for state in lifecycle_states
        if isinstance(state, dict)
        and state.get("status") == "active"
        and state.get("agent_class") in covered_by
    ]
    return {
        "repository_name": repository_name,
        "covering_agent_classes": covered_by,
        "active_agent_ids": active_agents,
    }


def build_agent_inventory(
    lifecycle_states: List[Dict[str, Any]],
    capability_profiles: List[Dict[str, Any]],
) -> Dict[str, Any]:
    status_counts = Counter(
        str(state.get("status", "unknown")) for state in lifecycle_states if isinstance(state, dict)
    )
    health_counts = Counter(
        str(state.get("health", "unknown")) for state in lifecycle_states if isinstance(state, dict)
    )
    return {
        "agent_count": len([s for s in lifecycle_states if isinstance(s, dict)]),
        "capability_profile_count": len([p for p in capability_profiles if isinstance(p, dict)]),
        "status_counts": dict(status_counts),
        "health_counts": dict(health_counts),
    }


def build_repository_coverage_matrix(capability_profiles: List[Dict[str, Any]]) -> Dict[str, Any]:
    coverage: Dict[str, Dict[str, List[str]]] = {}
    for profile in capability_profiles:
        if not isinstance(profile, dict):
            continue
        agent_class = str(profile.get("agent_class", "unknown"))
        repos = profile.get("repositories", [])
        for repo in repos if isinstance(repos, list) else []:
            repo_name = str(repo)
            if repo_name not in coverage:
                coverage[repo_name] = {"primary": [], "twin": []}
            primary_roles = profile.get("primary_roles", [])
            secondary_roles = profile.get("secondary_roles", [])
            if isinstance(primary_roles, list) and primary_roles:
                coverage[repo_name]["primary"].append(agent_class)
            if isinstance(secondary_roles, list) and secondary_roles:
                coverage[repo_name]["twin"].append(agent_class)
    return coverage

