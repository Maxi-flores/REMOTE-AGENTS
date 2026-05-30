from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal


PanelStatus = Literal["healthy", "warning", "degraded", "failing", "unknown"]
PANEL_STATUSES = {"healthy", "warning", "degraded", "failing", "unknown"}


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


@dataclass
class PanelViewModel:
    panel_id: str
    title: str
    status: PanelStatus
    summary: str
    metrics: Dict[str, Any] = field(default_factory=dict)
    cards: List[Dict[str, Any]] = field(default_factory=list)
    tables: List[Dict[str, Any]] = field(default_factory=list)
    timelines: List[Dict[str, Any]] = field(default_factory=list)
    graph_nodes: List[Dict[str, Any]] = field(default_factory=list)
    graph_edges: List[Dict[str, Any]] = field(default_factory=list)
    alerts: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "panel_id": self.panel_id,
            "title": self.title,
            "status": self.status,
            "summary": self.summary,
            "metrics": dict(self.metrics),
            "cards": list(self.cards),
            "tables": list(self.tables),
            "timelines": list(self.timelines),
            "graph_nodes": list(self.graph_nodes),
            "graph_edges": list(self.graph_edges),
            "alerts": list(self.alerts),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "PanelViewModel":
        validate_panel_view_model_dict(payload)
        return cls(
            panel_id=payload["panel_id"],
            title=payload["title"],
            status=payload["status"],
            summary=str(payload.get("summary") or ""),
            metrics=dict(payload.get("metrics") or {}),
            cards=list(payload.get("cards") or []),
            tables=list(payload.get("tables") or []),
            timelines=list(payload.get("timelines") or []),
            graph_nodes=list(payload.get("graph_nodes") or []),
            graph_edges=list(payload.get("graph_edges") or []),
            alerts=list(payload.get("alerts") or []),
            metadata=dict(payload.get("metadata") or {}),
        )


@dataclass
class ViewModelEnvelope:
    view_model_id: str
    generated_utc: str
    source_snapshot_id: str
    schema_version: int
    runtime_panel: Dict[str, Any]
    mission_panel: Dict[str, Any]
    agent_panel: Dict[str, Any]
    repository_panel: Dict[str, Any]
    tool_panel: Dict[str, Any]
    scheduler_panel: Dict[str, Any]
    memory_panel: Dict[str, Any]
    approval_panel: Dict[str, Any]
    consensus_panel: Dict[str, Any]
    observability_panel: Dict[str, Any]
    alerts: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "view_model_id": self.view_model_id,
            "generated_utc": self.generated_utc,
            "source_snapshot_id": self.source_snapshot_id,
            "schema_version": int(self.schema_version),
            "runtime_panel": dict(self.runtime_panel),
            "mission_panel": dict(self.mission_panel),
            "agent_panel": dict(self.agent_panel),
            "repository_panel": dict(self.repository_panel),
            "tool_panel": dict(self.tool_panel),
            "scheduler_panel": dict(self.scheduler_panel),
            "memory_panel": dict(self.memory_panel),
            "approval_panel": dict(self.approval_panel),
            "consensus_panel": dict(self.consensus_panel),
            "observability_panel": dict(self.observability_panel),
            "alerts": list(self.alerts),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "ViewModelEnvelope":
        validate_view_model_envelope_dict(payload)
        return cls(
            view_model_id=payload["view_model_id"],
            generated_utc=payload["generated_utc"],
            source_snapshot_id=payload["source_snapshot_id"],
            schema_version=int(payload["schema_version"]),
            runtime_panel=dict(payload["runtime_panel"]),
            mission_panel=dict(payload["mission_panel"]),
            agent_panel=dict(payload["agent_panel"]),
            repository_panel=dict(payload["repository_panel"]),
            tool_panel=dict(payload["tool_panel"]),
            scheduler_panel=dict(payload["scheduler_panel"]),
            memory_panel=dict(payload["memory_panel"]),
            approval_panel=dict(payload["approval_panel"]),
            consensus_panel=dict(payload["consensus_panel"]),
            observability_panel=dict(payload["observability_panel"]),
            alerts=list(payload.get("alerts") or []),
            metadata=dict(payload.get("metadata") or {}),
        )


def validate_view_model_envelope_dict(payload: Dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ValueError("ViewModelEnvelope must be an object")
    _require_str(payload, "view_model_id")
    _require_str(payload, "generated_utc")
    _require_str(payload, "source_snapshot_id")
    if isinstance(payload.get("schema_version"), bool) or not isinstance(payload.get("schema_version"), int):
        raise ValueError("schema_version is required and must be an integer")
    for key in (
        "runtime_panel",
        "mission_panel",
        "agent_panel",
        "repository_panel",
        "tool_panel",
        "scheduler_panel",
        "memory_panel",
        "approval_panel",
        "consensus_panel",
        "observability_panel",
    ):
        if not isinstance(payload.get(key), dict):
            raise ValueError(f"{key} must be an object")
    if not isinstance(payload.get("alerts", []), list):
        raise ValueError("alerts must be a list")
    if not isinstance(payload.get("metadata", {}), dict):
        raise ValueError("metadata must be an object")


def validate_panel_view_model_dict(payload: Dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ValueError("PanelViewModel must be an object")
    _require_str(payload, "panel_id")
    _require_str(payload, "title")
    status = _require_str(payload, "status")
    if status not in PANEL_STATUSES:
        raise ValueError(f"invalid panel status: {status}")
    if not isinstance(payload.get("metrics", {}), dict):
        raise ValueError("metrics must be an object")
    for key in ("cards", "tables", "timelines", "graph_nodes", "graph_edges", "alerts"):
        if not isinstance(payload.get(key, []), list):
            raise ValueError(f"{key} must be a list")
    if not isinstance(payload.get("metadata", {}), dict):
        raise ValueError("metadata must be an object")


def _require_str(payload: Dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} is required")
    return value

