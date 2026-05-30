from __future__ import annotations

from typing import Any, Dict, List


def build_agent_capability_matrix_panel(capability_profiles: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "panel_id": "agent_capability_matrix_panel",
        "title": "Agent Capability Matrix",
        "status": "healthy",
        "summary": "Capability profiles by agent class and repository coverage.",
        "metrics": {"profile_count": len(capability_profiles)},
        "cards": [{"label": "Capability Profiles", "value": len(capability_profiles)}],
        "tables": [
            {
                "id": "capability_matrix",
                "rows": [
                    {
                        "agent_class": profile.get("agent_class"),
                        "repositories": len(profile.get("repositories", [])) if isinstance(profile.get("repositories"), list) else 0,
                        "status": profile.get("status"),
                        "risk_tier": profile.get("risk_tier"),
                    }
                    for profile in capability_profiles
                    if isinstance(profile, dict)
                ],
            }
        ],
        "timelines": [],
        "graph_nodes": [],
        "graph_edges": [],
        "alerts": [],
        "metadata": {"advisory_only": True},
    }


def build_lifecycle_status_panel(lifecycle_states: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "panel_id": "lifecycle_status_panel",
        "title": "Lifecycle Status",
        "status": "healthy",
        "summary": "Lifecycle states by status/health/availability.",
        "metrics": {"state_count": len(lifecycle_states)},
        "cards": [{"label": "Lifecycle States", "value": len(lifecycle_states)}],
        "tables": [
            {
                "id": "lifecycle_states",
                "rows": [
                    {
                        "agent_id": state.get("agent_id"),
                        "agent_class": state.get("agent_class"),
                        "status": state.get("status"),
                        "health": state.get("health"),
                        "availability": state.get("availability"),
                    }
                    for state in lifecycle_states
                    if isinstance(state, dict)
                ],
            }
        ],
        "timelines": [],
        "graph_nodes": [],
        "graph_edges": [],
        "alerts": [],
        "metadata": {"advisory_only": True},
    }


def build_repository_coverage_panel(capability_profiles: List[Dict[str, Any]]) -> Dict[str, Any]:
    coverage: Dict[str, int] = {}
    for profile in capability_profiles:
        if not isinstance(profile, dict):
            continue
        for repo in profile.get("repositories", []) if isinstance(profile.get("repositories"), list) else []:
            coverage[str(repo)] = coverage.get(str(repo), 0) + 1
    return {
        "panel_id": "repository_coverage_panel",
        "title": "Repository Coverage",
        "status": "healthy",
        "summary": "Repository coverage by mapped agent capability profiles.",
        "metrics": {"repository_count": len(coverage)},
        "cards": [{"label": "Covered Repositories", "value": len(coverage)}],
        "tables": [{"id": "repository_coverage", "rows": [{"repository": k, "agent_count": v} for k, v in sorted(coverage.items())]}],
        "timelines": [],
        "graph_nodes": [],
        "graph_edges": [],
        "alerts": [],
        "metadata": {"advisory_only": True},
    }

