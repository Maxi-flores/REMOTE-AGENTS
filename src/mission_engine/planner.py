from __future__ import annotations

from typing import Any

from routers.repo_governance_router import resolve_repo_governance_route

from .contracts import Mission, create_task, utc_now


def plan_mission(mission: Mission) -> Mission:
    """Create one pending task per target repository.

    If no repository is supplied, create one fallback diagnostic task. Routing is
    delegated to the existing governance router for compatibility.
    """

    repositories = list(mission.target_repositories)
    if not repositories and mission.target_repository:
        repositories = [mission.target_repository]
    if not repositories:
        repositories = [None]

    tasks = []
    for repo in repositories:
        payload: dict[str, Any] = {}
        if repo:
            payload["target_repository"] = repo
        route = resolve_repo_governance_route(payload)
        task = create_task(
            mission_id=mission.mission_id,
            instruction=mission.instruction,
            target_repository=repo,
            assigned_primary_agent=route.primary_agent_class,
            assigned_twin_agent=route.twin_agent_class,
            priority=mission.priority,
        )
        tasks.append(task)

    mission.tasks = tasks
    mission.status = "planned"
    mission.updated_utc = utc_now()
    return mission

