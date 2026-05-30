from __future__ import annotations

from pathlib import Path
from typing import Any

from .mission_ingest import agent_node_id, mission_node_id, repository_node_id
from .store import MemoryGraphStore


def _store(store: MemoryGraphStore | None = None, graph_path: str | Path | None = None) -> MemoryGraphStore:
    if store is not None:
        return store
    if graph_path is not None:
        return MemoryGraphStore(graph_path)
    return MemoryGraphStore()


def find_node(node_id: str, *, store: MemoryGraphStore | None = None, graph_path: str | Path | None = None) -> dict[str, Any] | None:
    return _store(store, graph_path).get_node(node_id)


def find_nodes_by_type(
    node_type: str,
    *,
    store: MemoryGraphStore | None = None,
    graph_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    return _store(store, graph_path).list_nodes_by_type(node_type)


def find_neighbors(
    node_id: str,
    *,
    store: MemoryGraphStore | None = None,
    graph_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    graph_store = _store(store, graph_path)
    neighbors: list[dict[str, Any]] = []
    seen: set[str] = set()
    for edge in graph_store.list_edges_for_node(node_id):
        other_id = edge["to_node_id"] if edge.get("from_node_id") == node_id else edge.get("from_node_id")
        if not isinstance(other_id, str) or other_id in seen:
            continue
        node = graph_store.get_node(other_id)
        if node is not None:
            neighbors.append(node)
            seen.add(other_id)
    return neighbors


def find_repository_missions(
    repository_name: str,
    *,
    store: MemoryGraphStore | None = None,
    graph_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    graph_store = _store(store, graph_path)
    repo_id = repository_node_id(repository_name)
    missions: list[dict[str, Any]] = []
    for edge in graph_store.list_edges_for_node(repo_id):
        if edge.get("edge_type") != "targets_repository":
            continue
        other_id = edge["from_node_id"] if edge.get("to_node_id") == repo_id else edge.get("to_node_id")
        node = graph_store.get_node(str(other_id))
        if node and node.get("node_type") == "mission":
            missions.append(node)
    return missions


def find_agent_tasks(
    agent_class: str,
    *,
    store: MemoryGraphStore | None = None,
    graph_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    graph_store = _store(store, graph_path)
    aid = agent_node_id(agent_class)
    tasks: list[dict[str, Any]] = []
    for edge in graph_store.list_edges_for_node(aid):
        if edge.get("edge_type") not in ("assigned_to", "reviewed_by"):
            continue
        other_id = edge["from_node_id"] if edge.get("to_node_id") == aid else edge.get("to_node_id")
        node = graph_store.get_node(str(other_id))
        if node and node.get("node_type") == "task":
            tasks.append(node)
    return tasks


def find_mission_subgraph(
    mission_id: str,
    *,
    store: MemoryGraphStore | None = None,
    graph_path: str | Path | None = None,
) -> dict[str, dict[str, Any]]:
    graph_store = _store(store, graph_path)
    root_id = mission_node_id(mission_id)
    graph = graph_store.load_graph()
    node_ids: set[str] = {root_id}
    edge_ids: set[str] = set()
    frontier = [root_id]
    while frontier:
        current = frontier.pop()
        for edge in graph_store.list_edges_for_node(current):
            edge_id = str(edge["edge_id"])
            if edge_id in edge_ids:
                continue
            edge_ids.add(edge_id)
            for key in ("from_node_id", "to_node_id"):
                nid = str(edge.get(key))
                if nid and nid not in node_ids:
                    node_ids.add(nid)
                    frontier.append(nid)
    return {
        "nodes": {nid: graph["nodes"][nid] for nid in sorted(node_ids) if nid in graph["nodes"]},
        "edges": {eid: graph["edges"][eid] for eid in sorted(edge_ids) if eid in graph["edges"]},
    }

