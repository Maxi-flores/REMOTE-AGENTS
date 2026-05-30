from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

from .contracts import GraphEdge, GraphNode, validate_edge_dict, validate_node_dict


class MemoryGraphStore:
    """Local JSON store for the Semantic Memory Graph MVP."""

    def __init__(self, graph_path: str | Path = ".memory/graph.json") -> None:
        self.graph_path = Path(graph_path)

    def load_graph(self) -> dict[str, Any]:
        if not self.graph_path.exists():
            return {"schema_version": 1, "nodes": {}, "edges": {}}
        with self.graph_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("graph file must contain an object")
        nodes = data.get("nodes")
        edges = data.get("edges")
        if not isinstance(nodes, dict):
            nodes = {}
        if not isinstance(edges, dict):
            edges = {}
        graph = {"schema_version": int(data.get("schema_version") or 1), "nodes": nodes, "edges": edges}
        for node in graph["nodes"].values():
            if isinstance(node, dict):
                validate_node_dict(node)
        for edge in graph["edges"].values():
            if isinstance(edge, dict):
                validate_edge_dict(edge)
        return graph

    def save_graph(self, graph: dict[str, Any]) -> None:
        payload = {
            "schema_version": int(graph.get("schema_version") or 1),
            "nodes": dict(graph.get("nodes") or {}),
            "edges": dict(graph.get("edges") or {}),
        }
        for node in payload["nodes"].values():
            if isinstance(node, dict):
                validate_node_dict(node)
        for edge in payload["edges"].values():
            if isinstance(edge, dict):
                validate_edge_dict(edge)
        self.graph_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.graph_path.with_name(f".{self.graph_path.name}.tmp.{os.getpid()}.{int(time.time() * 1000)}")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.graph_path)

    def upsert_node(self, node: GraphNode | dict[str, Any]) -> dict[str, Any]:
        payload = node.to_dict() if isinstance(node, GraphNode) else dict(node)
        validate_node_dict(payload)
        graph = self.load_graph()
        existing = graph["nodes"].get(payload["node_id"])
        if isinstance(existing, dict):
            merged = dict(existing)
            merged.update(payload)
            metadata = dict(existing.get("metadata") or {})
            metadata.update(payload.get("metadata") or {})
            merged["metadata"] = metadata
            payload = merged
        graph["nodes"][payload["node_id"]] = payload
        self.save_graph(graph)
        return payload

    def upsert_edge(self, edge: GraphEdge | dict[str, Any]) -> dict[str, Any]:
        payload = edge.to_dict() if isinstance(edge, GraphEdge) else dict(edge)
        validate_edge_dict(payload)
        graph = self.load_graph()
        existing = graph["edges"].get(payload["edge_id"])
        if isinstance(existing, dict):
            merged = dict(existing)
            merged.update(payload)
            metadata = dict(existing.get("metadata") or {})
            metadata.update(payload.get("metadata") or {})
            merged["metadata"] = metadata
            payload = merged
        graph["edges"][payload["edge_id"]] = payload
        self.save_graph(graph)
        return payload

    def get_node(self, node_id: str) -> dict[str, Any] | None:
        node = self.load_graph()["nodes"].get(str(node_id))
        return dict(node) if isinstance(node, dict) else None

    def list_nodes_by_type(self, node_type: str) -> list[dict[str, Any]]:
        nodes = self.load_graph()["nodes"].values()
        return [dict(node) for node in nodes if isinstance(node, dict) and node.get("node_type") == node_type]

    def list_edges_for_node(self, node_id: str) -> list[dict[str, Any]]:
        nid = str(node_id)
        edges = self.load_graph()["edges"].values()
        return [
            dict(edge)
            for edge in edges
            if isinstance(edge, dict) and (edge.get("from_node_id") == nid or edge.get("to_node_id") == nid)
        ]

    def list_edges_by_type(self, edge_type: str) -> list[dict[str, Any]]:
        edges = self.load_graph()["edges"].values()
        return [dict(edge) for edge in edges if isinstance(edge, dict) and edge.get("edge_type") == edge_type]

