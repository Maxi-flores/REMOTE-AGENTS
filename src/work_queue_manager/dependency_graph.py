from __future__ import annotations

from typing import Any, Dict, List, Tuple


def infer_dependencies(refined_packages: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    by_id = {str(pkg.get("refined_package_id")): pkg for pkg in refined_packages if isinstance(pkg, dict)}
    deps: Dict[str, List[str]] = {}
    for pkg_id, pkg in by_id.items():
        deps[pkg_id] = _deps_for_package(pkg, by_id)
    return deps


def build_blockers(dependency_map: Dict[str, List[str]], known_ids: List[str]) -> List[Dict[str, Any]]:
    known = set(known_ids)
    blockers: List[Dict[str, Any]] = []
    for pkg_id, dep_ids in dependency_map.items():
        missing = [dep for dep in dep_ids if dep not in known]
        if missing:
            blockers.append(
                {
                    "queue_item_ref": pkg_id,
                    "type": "missing_artifact",
                    "missing_dependencies": missing,
                    "count": len(missing),
                }
            )
    return blockers


def topological_order(dependency_map: Dict[str, List[str]]) -> List[str]:
    visited: Dict[str, int] = {}
    order: List[str] = []

    def visit(node: str) -> None:
        if visited.get(node) == 1:
            return
        if visited.get(node) == -1:
            return
        visited[node] = -1
        for dep in dependency_map.get(node, []):
            if dep in dependency_map:
                visit(dep)
        visited[node] = 1
        order.append(node)

    for n in dependency_map:
        visit(n)
    return order


def _deps_for_package(pkg: Dict[str, Any], by_id: Dict[str, Dict[str, Any]]) -> List[str]:
    subsystem = str(pkg.get("subsystem") or "").lower()
    change_type = str(pkg.get("change_type") or "").lower()
    title = str(pkg.get("title") or "").lower()
    deps: List[str] = []

    # Deterministic rules
    if change_type == "add_cli_test":
        deps.extend(_find_candidates(by_id, subsystem=subsystem, change_type="add_test"))
    if change_type == "add_contract_test":
        deps.extend(_find_candidates(by_id, subsystem=subsystem, change_type="add_update"))
    if change_type == "add_docs" and "release" in subsystem:
        deps.extend(_find_candidates(by_id, subsystem=subsystem, change_type="add_update"))
    if "compat" in change_type or "compat" in title:
        deps.extend(_find_candidates(by_id, subsystem=subsystem, change_type="add_test"))

    # ensure no self refs
    pkg_id = str(pkg.get("refined_package_id") or "")
    unique = []
    seen = set()
    for dep in deps:
        if dep == pkg_id or dep in seen:
            continue
        seen.add(dep)
        unique.append(dep)
    return unique


def _find_candidates(by_id: Dict[str, Dict[str, Any]], *, subsystem: str, change_type: str) -> List[str]:
    out: List[str] = []
    for pkg_id, pkg in by_id.items():
        if str(pkg.get("subsystem") or "").lower() == subsystem and str(pkg.get("change_type") or "").lower() == change_type:
            out.append(pkg_id)
    return out
