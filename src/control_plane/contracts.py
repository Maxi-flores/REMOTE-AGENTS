from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal


SectionStatus = Literal["healthy", "warning", "degraded", "failing", "unknown"]
SECTION_STATUSES = {"healthy", "warning", "degraded", "failing", "unknown"}


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


@dataclass
class DashboardSection:
    section_id: str
    title: str
    status: SectionStatus
    summary: str
    metrics: Dict[str, Any] = field(default_factory=dict)
    records: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "section_id": self.section_id,
            "title": self.title,
            "status": self.status,
            "summary": self.summary,
            "metrics": dict(self.metrics),
            "records": list(self.records),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "DashboardSection":
        validate_dashboard_section_dict(payload)
        return cls(
            section_id=payload["section_id"],
            title=payload["title"],
            status=payload["status"],
            summary=str(payload.get("summary") or ""),
            metrics=dict(payload.get("metrics") or {}),
            records=list(payload.get("records") or []),
            warnings=[str(w) for w in payload.get("warnings", []) if isinstance(w, str)],
            errors=[str(e) for e in payload.get("errors", []) if isinstance(e, str)],
            metadata=dict(payload.get("metadata") or {}),
        )


@dataclass
class ControlPlaneSnapshot:
    snapshot_id: str
    generated_utc: str
    schema_version: int
    runtime: Dict[str, Any]
    missions: Dict[str, Any]
    agents: Dict[str, Any]
    repositories: Dict[str, Any]
    tools: Dict[str, Any]
    scheduler: Dict[str, Any]
    memory_graph: Dict[str, Any]
    approvals: Dict[str, Any]
    consensus: Dict[str, Any]
    queue: Dict[str, Any]
    observability: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "generated_utc": self.generated_utc,
            "schema_version": int(self.schema_version),
            "runtime": dict(self.runtime),
            "missions": dict(self.missions),
            "agents": dict(self.agents),
            "repositories": dict(self.repositories),
            "tools": dict(self.tools),
            "scheduler": dict(self.scheduler),
            "memory_graph": dict(self.memory_graph),
            "approvals": dict(self.approvals),
            "consensus": dict(self.consensus),
            "queue": dict(self.queue),
            "observability": dict(self.observability),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "ControlPlaneSnapshot":
        validate_control_plane_snapshot_dict(payload)
        return cls(
            snapshot_id=payload["snapshot_id"],
            generated_utc=payload["generated_utc"],
            schema_version=int(payload["schema_version"]),
            runtime=dict(payload["runtime"]),
            missions=dict(payload["missions"]),
            agents=dict(payload["agents"]),
            repositories=dict(payload["repositories"]),
            tools=dict(payload["tools"]),
            scheduler=dict(payload["scheduler"]),
            memory_graph=dict(payload["memory_graph"]),
            approvals=dict(payload["approvals"]),
            consensus=dict(payload["consensus"]),
            queue=dict(payload["queue"]),
            observability=dict(payload["observability"]),
            metadata=dict(payload.get("metadata") or {}),
        )


def validate_dashboard_section_dict(payload: Dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ValueError("DashboardSection must be an object")
    _require_str(payload, "section_id")
    _require_str(payload, "title")
    status = _require_str(payload, "status")
    if status not in SECTION_STATUSES:
        raise ValueError(f"invalid section status: {status}")
    if not isinstance(payload.get("metrics", {}), dict):
        raise ValueError("metrics must be an object")
    for key in ("records", "warnings", "errors"):
        if not isinstance(payload.get(key, []), list):
            raise ValueError(f"{key} must be a list")
    if not isinstance(payload.get("metadata", {}), dict):
        raise ValueError("metadata must be an object")


def validate_control_plane_snapshot_dict(payload: Dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ValueError("ControlPlaneSnapshot must be an object")
    _require_str(payload, "snapshot_id")
    _require_str(payload, "generated_utc")
    if isinstance(payload.get("schema_version"), bool) or not isinstance(payload.get("schema_version"), int):
        raise ValueError("schema_version is required and must be an integer")
    for key in (
        "runtime",
        "missions",
        "agents",
        "repositories",
        "tools",
        "scheduler",
        "memory_graph",
        "approvals",
        "consensus",
        "queue",
        "observability",
    ):
        if not isinstance(payload.get(key), dict):
            raise ValueError(f"{key} must be an object")
    if not isinstance(payload.get("metadata", {}), dict):
        raise ValueError("metadata must be an object")


def _require_str(payload: Dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} is required")
    return value

