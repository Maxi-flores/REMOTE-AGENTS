from __future__ import annotations

from typing import Dict, List, Set


def build_dependency_graph(records: List[dict]) -> Dict[str, List[str]]:
    graph: Dict[str, List[str]] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        repo = str(record.get("repository_id") or "").strip()
        if not repo:
            continue
        deps = record.get("depends_on") if isinstance(record.get("depends_on"), list) else []
        graph[repo] = [str(d).strip() for d in deps if str(d).strip()]
    return graph


def build_consumers_map(graph: Dict[str, List[str]]) -> Dict[str, List[str]]:
    consumers: Dict[str, List[str]] = {}
    for repo, deps in graph.items():
        consumers.setdefault(repo, [])
        for dep in deps:
            consumers.setdefault(dep, []).append(repo)
    for key in list(consumers.keys()):
        consumers[key] = sorted(set(consumers[key]))
    return consumers


def build_dependency_chains(graph: Dict[str, List[str]]) -> List[List[str]]:
    chains: List[List[str]] = []
    seen: Set[str] = set()

    def dfs(path: List[str], node: str) -> None:
        deps = graph.get(node, [])
        if not deps:
            key = "->".join(path)
            if key not in seen and len(path) > 1:
                seen.add(key)
                chains.append(path[:])
            return
        extended = False
        for dep in deps:
            if dep in path:
                continue
            extended = True
            dfs(path + [dep], dep)
        if not extended:
            key = "->".join(path)
            if key not in seen and len(path) > 1:
                seen.add(key)
                chains.append(path[:])

    for root in sorted(graph.keys()):
        dfs([root], root)
    return chains

