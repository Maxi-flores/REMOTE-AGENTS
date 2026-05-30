from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal


NodeType = Literal[
    "repository",
    "mission",
    "task",
    "agent",
    "tool",
    "approval",
    "consensus",
    "artifact",
    "incident",
    "decision",
    "policy",
    "model",
]

EdgeType = Literal[
    "contains",
    "assigned_to",
    "reviewed_by",
    "approved_by",
    "rejected_by",
    "uses_tool",
    "targets_repository",
    "produced_artifact",
    "caused_incident",
    "resolved_by",
    "depends_on",
    "relates_to",
    "governed_by",
    "generated_from",
    "remembered_as",
]

NODE_TYPES: set[str] = {
    "repository",
    "mission",
    "task",
    "agent",
    "tool",
    "approval",
    "consensus",
    "artifact",
    "incident",
    "decision",
    "policy",
    "model",
}

EDGE_TYPES: set[str] = {
    "contains",
    "assigned_to",
    "reviewed_by",
    "approved_by",
    "rejected_by",
    "uses_tool",
    "targets_repository",
    "produced_artifact",
    "caused_incident",
    "resolved_by",
    "depends_on",
    "relates_to",
    "governed_by",
    "generated_from",
    "remembered_as",
}


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


@dataclass(slots=True)
class GraphNode:
    node_id: str
    node_type: NodeType
    label: str
    source: str
    created_utc: str = field(default_factory=utc_now)
    updated_utc: str = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "label": self.label,
            "created_utc": self.created_utc,
            "updated_utc": self.updated_utc,
            "source": self.source,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GraphNode":
        validate_node_dict(data)
        return cls(
            node_id=str(data["node_id"]),
            node_type=str(data["node_type"]),  # type: ignore[arg-type]
            label=str(data["label"]),
            created_utc=str(data["created_utc"]),
            updated_utc=str(data["updated_utc"]),
            source=str(data["source"]),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass(slots=True)
class GraphEdge:
    edge_id: str
    from_node_id: str
    to_node_id: str
    edge_type: EdgeType
    source: str
    created_utc: str = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "from_node_id": self.from_node_id,
            "to_node_id": self.to_node_id,
            "edge_type": self.edge_type,
            "created_utc": self.created_utc,
            "source": self.source,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GraphEdge":
        validate_edge_dict(data)
        return cls(
            edge_id=str(data["edge_id"]),
            from_node_id=str(data["from_node_id"]),
            to_node_id=str(data["to_node_id"]),
            edge_type=str(data["edge_type"]),  # type: ignore[arg-type]
            created_utc=str(data["created_utc"]),
            source=str(data["source"]),
            metadata=dict(data.get("metadata") or {}),
        )


def create_node(
    *,
    node_type: NodeType,
    label: str,
    source: str = "memory-graph",
    node_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> GraphNode:
    prefix = str(node_type).replace("_", "-")
    node = GraphNode(
        node_id=node_id or new_id(prefix),
        node_type=node_type,
        label=str(label),
        source=str(source),
        metadata=dict(metadata or {}),
    )
    validate_node_dict(node.to_dict())
    return node


def create_edge(
    *,
    from_node_id: str,
    to_node_id: str,
    edge_type: EdgeType,
    source: str = "memory-graph",
    edge_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> GraphEdge:
    edge = GraphEdge(
        edge_id=edge_id or deterministic_edge_id(from_node_id, edge_type, to_node_id),
        from_node_id=str(from_node_id),
        to_node_id=str(to_node_id),
        edge_type=edge_type,
        source=str(source),
        metadata=dict(metadata or {}),
    )
    validate_edge_dict(edge.to_dict())
    return edge


def deterministic_edge_id(from_node_id: str, edge_type: str, to_node_id: str) -> str:
    raw = f"{from_node_id}::{edge_type}::{to_node_id}"
    safe = "".join(ch if ch.isalnum() else "_" for ch in raw)
    return f"edge_{safe[:180]}"


def validate_node_dict(data: dict[str, Any]) -> None:
    if not isinstance(data, dict):
        raise ValueError("graph node must be an object")
    _require_str(data, "node_id")
    _require_str(data, "node_type")
    if data["node_type"] not in NODE_TYPES:
        raise ValueError(f"invalid node_type: {data['node_type']}")
    _require_str(data, "label")
    _require_str(data, "created_utc")
    _require_str(data, "updated_utc")
    _require_str(data, "source")
    if not isinstance(data.get("metadata"), dict):
        raise ValueError("node metadata must be an object")


def validate_edge_dict(data: dict[str, Any]) -> None:
    if not isinstance(data, dict):
        raise ValueError("graph edge must be an object")
    _require_str(data, "edge_id")
    _require_str(data, "from_node_id")
    _require_str(data, "to_node_id")
    _require_str(data, "edge_type")
    if data["edge_type"] not in EDGE_TYPES:
        raise ValueError(f"invalid edge_type: {data['edge_type']}")
    _require_str(data, "created_utc")
    _require_str(data, "source")
    if not isinstance(data.get("metadata"), dict):
        raise ValueError("edge metadata must be an object")


def _require_str(data: dict[str, Any], key: str) -> None:
    if not isinstance(data.get(key), str) or not str(data.get(key)).strip():
        raise ValueError(f"graph field {key!r} must be a non-empty string")

