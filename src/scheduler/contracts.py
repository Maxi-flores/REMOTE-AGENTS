from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional


WorkerType = Literal[
    "local_ollama",
    "local_codex",
    "local_claude_code",
    "local_mcp",
    "local_shell",
    "browser_runtime",
    "future_cloud",
]

WorkerStatus = Literal["registered", "idle", "busy", "degraded", "offline", "disabled"]
LeaseStatus = Literal["active", "renewed", "released", "expired", "failed", "cancelled"]

WORKER_TYPES = {
    "local_ollama",
    "local_codex",
    "local_claude_code",
    "local_mcp",
    "local_shell",
    "browser_runtime",
    "future_cloud",
}
WORKER_STATUSES = {"registered", "idle", "busy", "degraded", "offline", "disabled"}
LEASE_STATUSES = {"active", "renewed", "released", "expired", "failed", "cancelled"}


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


@dataclass
class WorkerDescriptor:
    worker_id: str
    worker_type: WorkerType
    display_name: str
    status: WorkerStatus
    capabilities: List[str] = field(default_factory=list)
    supported_providers: List[str] = field(default_factory=list)
    supported_repository_groups: List[str] = field(default_factory=list)
    max_concurrent_tasks: int = 1
    hardware_budget: Dict[str, Any] = field(default_factory=dict)
    created_utc: str = field(default_factory=utc_now)
    updated_utc: str = field(default_factory=utc_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "worker_type": self.worker_type,
            "display_name": self.display_name,
            "status": self.status,
            "capabilities": list(self.capabilities),
            "supported_providers": list(self.supported_providers),
            "supported_repository_groups": list(self.supported_repository_groups),
            "max_concurrent_tasks": int(self.max_concurrent_tasks),
            "hardware_budget": dict(self.hardware_budget),
            "created_utc": self.created_utc,
            "updated_utc": self.updated_utc,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "WorkerDescriptor":
        validate_worker_descriptor_dict(payload)
        return cls(
            worker_id=payload["worker_id"],
            worker_type=payload["worker_type"],
            display_name=payload["display_name"],
            status=payload["status"],
            capabilities=list(payload.get("capabilities") or []),
            supported_providers=list(payload.get("supported_providers") or []),
            supported_repository_groups=list(payload.get("supported_repository_groups") or []),
            max_concurrent_tasks=int(payload["max_concurrent_tasks"]),
            hardware_budget=dict(payload.get("hardware_budget") or {}),
            created_utc=payload["created_utc"],
            updated_utc=payload["updated_utc"],
            metadata=dict(payload.get("metadata") or {}),
        )


@dataclass
class TaskLease:
    lease_id: str
    task_id: str
    worker_id: str
    lease_status: LeaseStatus
    priority: int
    acquired_utc: str
    expires_utc: str
    mission_id: Optional[str] = None
    renewed_utc: Optional[str] = None
    released_utc: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lease_id": self.lease_id,
            "task_id": self.task_id,
            "mission_id": self.mission_id,
            "worker_id": self.worker_id,
            "lease_status": self.lease_status,
            "priority": int(self.priority),
            "acquired_utc": self.acquired_utc,
            "expires_utc": self.expires_utc,
            "renewed_utc": self.renewed_utc,
            "released_utc": self.released_utc,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "TaskLease":
        validate_task_lease_dict(payload)
        return cls(
            lease_id=payload["lease_id"],
            task_id=payload["task_id"],
            mission_id=_optional_str(payload.get("mission_id")),
            worker_id=payload["worker_id"],
            lease_status=payload["lease_status"],
            priority=int(payload["priority"]),
            acquired_utc=payload["acquired_utc"],
            expires_utc=payload["expires_utc"],
            renewed_utc=_optional_str(payload.get("renewed_utc")),
            released_utc=_optional_str(payload.get("released_utc")),
            metadata=dict(payload.get("metadata") or {}),
        )


def create_worker_descriptor(
    *,
    worker_id: Optional[str] = None,
    worker_type: WorkerType,
    display_name: str,
    status: WorkerStatus = "registered",
    capabilities: Optional[List[str]] = None,
    supported_providers: Optional[List[str]] = None,
    supported_repository_groups: Optional[List[str]] = None,
    max_concurrent_tasks: int = 1,
    hardware_budget: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> WorkerDescriptor:
    now = utc_now()
    worker = WorkerDescriptor(
        worker_id=worker_id or new_id("worker"),
        worker_type=worker_type,
        display_name=display_name,
        status=status,
        capabilities=list(capabilities or []),
        supported_providers=list(supported_providers or []),
        supported_repository_groups=list(supported_repository_groups or []),
        max_concurrent_tasks=max_concurrent_tasks,
        hardware_budget=dict(hardware_budget or {}),
        created_utc=now,
        updated_utc=now,
        metadata=dict(metadata or {}),
    )
    validate_worker_descriptor_dict(worker.to_dict())
    return worker


def create_task_lease(
    *,
    task_id: str,
    worker_id: str,
    expires_utc: str,
    mission_id: Optional[str] = None,
    priority: int = 0,
    lease_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> TaskLease:
    lease = TaskLease(
        lease_id=lease_id or new_id("lease"),
        task_id=task_id,
        mission_id=mission_id,
        worker_id=worker_id,
        lease_status="active",
        priority=priority,
        acquired_utc=utc_now(),
        expires_utc=expires_utc,
        metadata=dict(metadata or {}),
    )
    validate_task_lease_dict(lease.to_dict())
    return lease


def validate_worker_descriptor_dict(payload: Dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ValueError("WorkerDescriptor payload must be an object")
    _require_str(payload, "worker_id")
    worker_type = _require_str(payload, "worker_type")
    if worker_type not in WORKER_TYPES:
        raise ValueError(f"Invalid worker type: {worker_type}")
    _require_str(payload, "display_name")
    status = _require_str(payload, "status")
    if status not in WORKER_STATUSES:
        raise ValueError(f"Invalid worker status: {status}")
    _require_list(payload, "capabilities")
    _require_list(payload, "supported_providers")
    _require_list(payload, "supported_repository_groups")
    max_tasks = payload.get("max_concurrent_tasks")
    if isinstance(max_tasks, bool) or not isinstance(max_tasks, int) or max_tasks <= 0:
        raise ValueError("max_concurrent_tasks must be a positive integer")
    if not isinstance(payload.get("hardware_budget"), dict):
        raise ValueError("hardware_budget must be an object")
    _require_str(payload, "created_utc")
    _require_str(payload, "updated_utc")
    if not isinstance(payload.get("metadata"), dict):
        raise ValueError("metadata must be an object")


def validate_task_lease_dict(payload: Dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ValueError("TaskLease payload must be an object")
    _require_str(payload, "lease_id")
    _require_str(payload, "task_id")
    _require_str(payload, "worker_id")
    lease_status = _require_str(payload, "lease_status")
    if lease_status not in LEASE_STATUSES:
        raise ValueError(f"Invalid lease status: {lease_status}")
    _require_str(payload, "acquired_utc")
    _require_str(payload, "expires_utc")
    priority = payload.get("priority")
    if isinstance(priority, bool) or not isinstance(priority, int):
        raise ValueError("priority must be an integer")
    if not isinstance(payload.get("metadata"), dict):
        raise ValueError("metadata must be an object")


def _require_str(payload: Dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} is required")
    return value


def _require_list(payload: Dict[str, Any], key: str) -> None:
    if not isinstance(payload.get(key), list):
        raise ValueError(f"{key} must be a list")


def _optional_str(value: Any) -> Optional[str]:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None
