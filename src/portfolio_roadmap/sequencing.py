from __future__ import annotations

from typing import Any, Dict, List, Set


def priority_order(priority: str) -> int:
    return {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}.get(priority, 4)


def horizon_for_priority(priority: str) -> str:
    if priority in {"P0", "P1"}:
        return "near_term"
    if priority == "P2":
        return "mid_term"
    return "long_term"


def wave_for_horizon_and_depth(horizon: str, depth: int) -> str:
    if horizon == "near_term":
        return "wave_1" if depth <= 1 else "wave_2"
    if horizon == "mid_term":
        return "wave_2" if depth <= 1 else "wave_3"
    return "wave_3"


def dependency_depth(repository_id: str, dependency_graph: Dict[str, Any], _stack: Set[str] | None = None) -> int:
    stack = set(_stack or set())
    if repository_id in stack:
        return 0
    stack.add(repository_id)
    deps = dependency_graph.get(repository_id)
    if not isinstance(deps, list) or not deps:
        return 0
    max_depth = 0
    for dep in deps:
        dep_id = str(dep)
        max_depth = max(max_depth, 1 + dependency_depth(dep_id, dependency_graph, stack))
    return max_depth


def sequence_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        items,
        key=lambda item: (
            _horizon_order(str(item.get("horizon") or "long_term")),
            _wave_order(str(item.get("wave") or "wave_3")),
            priority_order(str(item.get("priority") or "P4")),
            str(item.get("repository_id") or ""),
            str(item.get("item_id") or ""),
        ),
    )


def _horizon_order(horizon: str) -> int:
    return {"near_term": 0, "mid_term": 1, "long_term": 2}.get(horizon, 2)


def _wave_order(wave: str) -> int:
    return {"wave_1": 0, "wave_2": 1, "wave_3": 2}.get(wave, 3)

