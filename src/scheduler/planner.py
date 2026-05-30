from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from scheduler.contracts import WorkerDescriptor
from tool_router.router import resolve_tool_route


BLOCKING_STATUSES = {"offline", "disabled"}


def choose_worker_for_task(task: Any, workers: Iterable[WorkerDescriptor | Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    candidates = []
    for raw_worker in workers:
        worker = raw_worker.to_dict() if isinstance(raw_worker, WorkerDescriptor) else dict(raw_worker)
        if worker.get("status") in BLOCKING_STATUSES:
            continue
        score = _score_worker(task, worker)
        if score < 0:
            continue
        candidates.append((score, worker.get("status") != "idle", worker.get("worker_id", ""), worker))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (-item[0], item[1], str(item[2])))
    return dict(candidates[0][3])


def estimate_task_risk(task: Any) -> str:
    required_tools = _task_list(task, "required_tools")
    instruction = _task_str(task, "instruction").lower()
    if any(resolve_tool_route(tool).risk_tier in {"critical", "high"} for tool in required_tools):
        return "high"
    if "write" in instruction or "execute" in instruction or "network" in instruction:
        return "high"
    if required_tools:
        return "medium"
    return "low"


def plan_task_schedule(task: Any, workers: Iterable[WorkerDescriptor | Dict[str, Any]]) -> Dict[str, Any]:
    worker = choose_worker_for_task(task, workers)
    if worker is None:
        return {
            "status": "blocked",
            "worker": None,
            "reason": "no_matching_available_worker",
            "risk_tier": estimate_task_risk(task),
            "task_id": _task_str(task, "task_id"),
            "queue_mutation": False,
        }
    return {
        "status": "planned",
        "worker": worker,
        "reason": "matching_worker_selected",
        "risk_tier": estimate_task_risk(task),
        "task_id": _task_str(task, "task_id"),
        "queue_mutation": False,
    }


def explain_schedule_decision(task: Any, worker: Optional[Dict[str, Any]], reason: str) -> Dict[str, Any]:
    return {
        "task_id": _task_str(task, "task_id"),
        "target_repository": _task_str(task, "target_repository") or None,
        "repository_group": _task_repository_group(task),
        "required_tools": _task_list(task, "required_tools"),
        "worker_id": worker.get("worker_id") if isinstance(worker, dict) else None,
        "worker_status": worker.get("status") if isinstance(worker, dict) else None,
        "reason": reason,
        "queue_mutation": False,
    }


def _score_worker(task: Any, worker: Dict[str, Any]) -> int:
    score = 0
    capabilities = set(_str_list(worker.get("capabilities")))
    providers = set(_str_list(worker.get("supported_providers")))
    repository_groups = set(_str_list(worker.get("supported_repository_groups")))
    required_tools = _task_list(task, "required_tools")
    required_providers = {resolve_tool_route(tool).provider for tool in required_tools}
    repository_group = _task_repository_group(task)

    if repository_group and repository_groups and repository_group not in repository_groups:
        return -1
    if repository_group and repository_group in repository_groups:
        score += 2

    for tool in required_tools:
        if tool in capabilities:
            score += 3
    for provider in required_providers:
        if provider in providers:
            score += 2
        elif providers:
            return -1

    if required_tools and not capabilities and not providers:
        return -1
    if worker.get("status") == "idle":
        score += 2
    elif worker.get("status") == "registered":
        score += 1
    elif worker.get("status") == "busy":
        score -= 1
    return score


def _task_repository_group(task: Any) -> Optional[str]:
    metadata = _task_metadata(task)
    value = metadata.get("repository_group") or metadata.get("target_repository_group")
    return value if isinstance(value, str) and value.strip() else None


def _task_metadata(task: Any) -> Dict[str, Any]:
    if isinstance(task, dict):
        metadata = task.get("metadata")
    else:
        metadata = getattr(task, "metadata", None)
    return dict(metadata) if isinstance(metadata, dict) else {}


def _task_str(task: Any, field_name: str) -> str:
    value = task.get(field_name) if isinstance(task, dict) else getattr(task, field_name, "")
    return value if isinstance(value, str) else ""


def _task_list(task: Any, field_name: str) -> List[str]:
    value = task.get(field_name) if isinstance(task, dict) else getattr(task, field_name, [])
    return _str_list(value)


def _str_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str)]
