from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Literal


MissionStatus = Literal[
    "draft",
    "planned",
    "awaiting_approval",
    "scheduled",
    "running",
    "validating",
    "completed",
    "failed",
    "cancelled",
    "archived",
]

TaskStatus = Literal[
    "pending",
    "queued",
    "running",
    "blocked",
    "completed",
    "failed",
    "skipped",
]

ApprovalAction = Literal["approve", "reject", "request_changes", "expire"]
ApprovalStatus = Literal["requested", "approved", "rejected", "changes_requested", "expired", "cancelled"]
ConsensusType = Literal["twin", "quorum", "human", "policy", "system"]
ConsensusDecision = Literal["approved", "rejected", "abstained", "changes_requested", "failed"]

MISSION_STATUSES: set[str] = {
    "draft",
    "planned",
    "awaiting_approval",
    "scheduled",
    "running",
    "validating",
    "completed",
    "failed",
    "cancelled",
    "archived",
}

TASK_STATUSES: set[str] = {
    "pending",
    "queued",
    "running",
    "blocked",
    "completed",
    "failed",
    "skipped",
}

APPROVAL_ACTIONS: set[str] = {"approve", "reject", "request_changes", "expire"}
APPROVAL_STATUSES: set[str] = {
    "requested",
    "approved",
    "rejected",
    "changes_requested",
    "expired",
    "cancelled",
}
CONSENSUS_TYPES: set[str] = {"twin", "quorum", "human", "policy", "system"}
CONSENSUS_DECISIONS: set[str] = {"approved", "rejected", "abstained", "changes_requested", "failed"}


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


@dataclass(slots=True)
class MissionTask:
    task_id: str
    mission_id: str
    instruction: str
    target_repository: str | None = None
    assigned_primary_agent: str | None = None
    assigned_twin_agent: str | None = None
    required_tools: list[str] = field(default_factory=list)
    status: TaskStatus = "pending"
    priority: int = 0
    depends_on: list[str] = field(default_factory=list)
    created_utc: str = field(default_factory=utc_now)
    updated_utc: str = field(default_factory=utc_now)
    queue_payload: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "mission_id": self.mission_id,
            "instruction": self.instruction,
            "target_repository": self.target_repository,
            "assigned_primary_agent": self.assigned_primary_agent,
            "assigned_twin_agent": self.assigned_twin_agent,
            "required_tools": list(self.required_tools),
            "status": self.status,
            "priority": int(self.priority),
            "depends_on": list(self.depends_on),
            "created_utc": self.created_utc,
            "updated_utc": self.updated_utc,
            "queue_payload": self.queue_payload,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MissionTask":
        validate_task_dict(data)
        return cls(
            task_id=str(data["task_id"]),
            mission_id=str(data["mission_id"]),
            instruction=str(data["instruction"]),
            target_repository=_optional_str(data.get("target_repository")),
            assigned_primary_agent=_optional_str(data.get("assigned_primary_agent")),
            assigned_twin_agent=_optional_str(data.get("assigned_twin_agent")),
            required_tools=_str_list(data.get("required_tools")),
            status=str(data.get("status", "pending")),  # type: ignore[arg-type]
            priority=_int_value(data.get("priority"), default=0),
            depends_on=_str_list(data.get("depends_on")),
            created_utc=str(data.get("created_utc") or utc_now()),
            updated_utc=str(data.get("updated_utc") or utc_now()),
            queue_payload=data.get("queue_payload") if isinstance(data.get("queue_payload"), dict) else None,
        )


@dataclass(slots=True)
class ApprovalRecord:
    approval_id: str
    mission_id: str
    action: ApprovalAction
    status: ApprovalStatus
    requested_by: str
    risk_tier: str
    task_id: str | None = None
    reviewed_by: str | None = None
    reason: str | None = None
    created_utc: str = field(default_factory=utc_now)
    updated_utc: str = field(default_factory=utc_now)
    expires_utc: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "approval_id": self.approval_id,
            "mission_id": self.mission_id,
            "task_id": self.task_id,
            "action": self.action,
            "status": self.status,
            "requested_by": self.requested_by,
            "reviewed_by": self.reviewed_by,
            "reason": self.reason,
            "risk_tier": self.risk_tier,
            "created_utc": self.created_utc,
            "updated_utc": self.updated_utc,
            "expires_utc": self.expires_utc,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ApprovalRecord":
        validate_approval_record_dict(data)
        return cls(
            approval_id=str(data["approval_id"]),
            mission_id=str(data["mission_id"]),
            task_id=_optional_str(data.get("task_id")),
            action=str(data["action"]),  # type: ignore[arg-type]
            status=str(data["status"]),  # type: ignore[arg-type]
            requested_by=str(data["requested_by"]),
            reviewed_by=_optional_str(data.get("reviewed_by")),
            reason=_optional_str(data.get("reason")),
            risk_tier=str(data["risk_tier"]),
            created_utc=str(data["created_utc"]),
            updated_utc=str(data["updated_utc"]),
            expires_utc=_optional_str(data.get("expires_utc")),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass(slots=True)
class ConsensusRecord:
    consensus_id: str
    mission_id: str
    consensus_type: ConsensusType
    decision: ConsensusDecision
    actor: str
    task_id: str | None = None
    agent_class: str | None = None
    tool_name: str | None = None
    target_repository: str | None = None
    feedback: str | None = None
    created_utc: str = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "consensus_id": self.consensus_id,
            "mission_id": self.mission_id,
            "task_id": self.task_id,
            "consensus_type": self.consensus_type,
            "decision": self.decision,
            "actor": self.actor,
            "agent_class": self.agent_class,
            "tool_name": self.tool_name,
            "target_repository": self.target_repository,
            "feedback": self.feedback,
            "created_utc": self.created_utc,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConsensusRecord":
        validate_consensus_record_dict(data)
        return cls(
            consensus_id=str(data["consensus_id"]),
            mission_id=str(data["mission_id"]),
            task_id=_optional_str(data.get("task_id")),
            consensus_type=str(data["consensus_type"]),  # type: ignore[arg-type]
            decision=str(data["decision"]),  # type: ignore[arg-type]
            actor=str(data["actor"]),
            agent_class=_optional_str(data.get("agent_class")),
            tool_name=_optional_str(data.get("tool_name")),
            target_repository=_optional_str(data.get("target_repository")),
            feedback=_optional_str(data.get("feedback")),
            created_utc=str(data["created_utc"]),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass(slots=True)
class Mission:
    mission_id: str
    title: str
    instruction: str
    target_repository: str | None = None
    target_repositories: list[str] = field(default_factory=list)
    priority: int = 0
    status: MissionStatus = "draft"
    risk_tier: str = "standard"
    created_utc: str = field(default_factory=utc_now)
    updated_utc: str = field(default_factory=utc_now)
    tasks: list[MissionTask] = field(default_factory=list)
    approvals: list[dict[str, Any]] = field(default_factory=list)
    consensus_records: list[dict[str, Any]] = field(default_factory=list)
    telemetry_events: list[dict[str, Any]] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    failure_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "mission_id": self.mission_id,
            "title": self.title,
            "instruction": self.instruction,
            "target_repository": self.target_repository,
            "target_repositories": list(self.target_repositories),
            "priority": int(self.priority),
            "status": self.status,
            "risk_tier": self.risk_tier,
            "created_utc": self.created_utc,
            "updated_utc": self.updated_utc,
            "tasks": [task.to_dict() for task in self.tasks],
            "approvals": list(self.approvals),
            "consensus_records": list(self.consensus_records),
            "telemetry_events": list(self.telemetry_events),
            "artifacts": list(self.artifacts),
            "failure_reason": self.failure_reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Mission":
        validate_mission_dict(data)
        tasks_raw = data.get("tasks") or []
        tasks = [MissionTask.from_dict(t) for t in tasks_raw if isinstance(t, dict)]
        return cls(
            mission_id=str(data["mission_id"]),
            title=str(data["title"]),
            instruction=str(data["instruction"]),
            target_repository=_optional_str(data.get("target_repository")),
            target_repositories=_str_list(data.get("target_repositories")),
            priority=_int_value(data.get("priority"), default=0),
            status=str(data.get("status", "draft")),  # type: ignore[arg-type]
            risk_tier=str(data.get("risk_tier") or "standard"),
            created_utc=str(data.get("created_utc") or utc_now()),
            updated_utc=str(data.get("updated_utc") or utc_now()),
            tasks=tasks,
            approvals=_dict_list(data.get("approvals")),
            consensus_records=_dict_list(data.get("consensus_records")),
            telemetry_events=_dict_list(data.get("telemetry_events")),
            artifacts=_dict_list(data.get("artifacts")),
            failure_reason=_optional_str(data.get("failure_reason")),
        )


def create_mission(
    *,
    title: str,
    instruction: str,
    target_repository: str | None = None,
    target_repositories: list[str] | None = None,
    priority: int = 0,
    risk_tier: str = "standard",
    status: MissionStatus = "draft",
    mission_id: str | None = None,
) -> Mission:
    repositories = _normalize_repositories(target_repository=target_repository, target_repositories=target_repositories)
    primary_repo = target_repository or (repositories[0] if repositories else None)
    now = utc_now()
    mission = Mission(
        mission_id=mission_id or new_id("mission"),
        title=str(title).strip(),
        instruction=str(instruction).strip(),
        target_repository=primary_repo,
        target_repositories=repositories,
        priority=_int_value(priority, default=0),
        status=status,
        risk_tier=str(risk_tier or "standard"),
        created_utc=now,
        updated_utc=now,
    )
    validate_mission_dict(mission.to_dict())
    return mission


def create_task(
    *,
    mission_id: str,
    instruction: str,
    target_repository: str | None,
    assigned_primary_agent: str | None,
    assigned_twin_agent: str | None,
    priority: int = 0,
    required_tools: list[str] | None = None,
    depends_on: list[str] | None = None,
    task_id: str | None = None,
) -> MissionTask:
    now = utc_now()
    task = MissionTask(
        task_id=task_id or new_id("task"),
        mission_id=str(mission_id),
        instruction=str(instruction).strip(),
        target_repository=target_repository,
        assigned_primary_agent=assigned_primary_agent,
        assigned_twin_agent=assigned_twin_agent,
        required_tools=list(required_tools or []),
        status="pending",
        priority=_int_value(priority, default=0),
        depends_on=list(depends_on or []),
        created_utc=now,
        updated_utc=now,
    )
    validate_task_dict(task.to_dict())
    return task


def create_approval_request(
    *,
    mission_id: str,
    requested_by: str,
    risk_tier: str,
    task_id: str | None = None,
    reason: str | None = None,
    expires_utc: str | None = None,
    metadata: dict[str, Any] | None = None,
    approval_id: str | None = None,
) -> ApprovalRecord:
    now = utc_now()
    record = ApprovalRecord(
        approval_id=approval_id or new_id("approval"),
        mission_id=str(mission_id),
        task_id=task_id,
        action="approve",
        status="requested",
        requested_by=str(requested_by),
        reason=reason,
        risk_tier=str(risk_tier),
        created_utc=now,
        updated_utc=now,
        expires_utc=expires_utc,
        metadata=dict(metadata or {}),
    )
    validate_approval_record_dict(record.to_dict())
    return record


def approve_record(record: ApprovalRecord | dict[str, Any], *, reviewed_by: str, reason: str | None = None) -> ApprovalRecord:
    return _transition_approval(record, action="approve", status="approved", reviewed_by=reviewed_by, reason=reason)


def reject_record(record: ApprovalRecord | dict[str, Any], *, reviewed_by: str, reason: str | None = None) -> ApprovalRecord:
    return _transition_approval(record, action="reject", status="rejected", reviewed_by=reviewed_by, reason=reason)


def request_changes_record(
    record: ApprovalRecord | dict[str, Any],
    *,
    reviewed_by: str,
    reason: str | None = None,
) -> ApprovalRecord:
    return _transition_approval(
        record,
        action="request_changes",
        status="changes_requested",
        reviewed_by=reviewed_by,
        reason=reason,
    )


def expire_record(record: ApprovalRecord | dict[str, Any], *, reason: str | None = None) -> ApprovalRecord:
    return _transition_approval(record, action="expire", status="expired", reviewed_by=None, reason=reason)


def create_consensus_record(
    *,
    mission_id: str,
    consensus_type: ConsensusType,
    decision: ConsensusDecision,
    actor: str,
    task_id: str | None = None,
    agent_class: str | None = None,
    tool_name: str | None = None,
    target_repository: str | None = None,
    feedback: str | None = None,
    metadata: dict[str, Any] | None = None,
    consensus_id: str | None = None,
) -> ConsensusRecord:
    record = ConsensusRecord(
        consensus_id=consensus_id or new_id("consensus"),
        mission_id=str(mission_id),
        task_id=task_id,
        consensus_type=consensus_type,
        decision=decision,
        actor=str(actor),
        agent_class=agent_class,
        tool_name=tool_name,
        target_repository=target_repository,
        feedback=feedback,
        metadata=dict(metadata or {}),
    )
    validate_consensus_record_dict(record.to_dict())
    return record


def validate_mission_dict(data: dict[str, Any]) -> None:
    if not isinstance(data, dict):
        raise ValueError("mission must be an object")
    _require_str(data, "mission_id")
    _require_str(data, "title")
    _require_str(data, "instruction")
    _require_str(data, "status")
    if data["status"] not in MISSION_STATUSES:
        raise ValueError(f"invalid mission status: {data['status']}")
    _require_str(data, "created_utc")
    _require_str(data, "updated_utc")
    _require_list(data, "tasks")
    for field_name in ("target_repositories", "approvals", "consensus_records", "telemetry_events", "artifacts"):
        _require_list(data, field_name)
    _int_value(data.get("priority"), default=0)
    for approval in data.get("approvals", []):
        if isinstance(approval, dict):
            validate_approval_record_dict(approval)
    for consensus in data.get("consensus_records", []):
        if isinstance(consensus, dict):
            validate_consensus_record_dict(consensus)


def validate_task_dict(data: dict[str, Any]) -> None:
    if not isinstance(data, dict):
        raise ValueError("task must be an object")
    _require_str(data, "task_id")
    _require_str(data, "mission_id")
    _require_str(data, "instruction")
    _require_str(data, "status")
    if data["status"] not in TASK_STATUSES:
        raise ValueError(f"invalid task status: {data['status']}")
    _require_str(data, "created_utc")
    _require_str(data, "updated_utc")
    _require_list(data, "required_tools")
    _require_list(data, "depends_on")
    _int_value(data.get("priority"), default=0)


def validate_approval_record_dict(data: dict[str, Any]) -> None:
    if not isinstance(data, dict):
        raise ValueError("approval record must be an object")
    _require_str(data, "approval_id")
    _require_str(data, "mission_id")
    _require_str(data, "action")
    if data["action"] not in APPROVAL_ACTIONS:
        raise ValueError(f"invalid approval action: {data['action']}")
    _require_str(data, "status")
    if data["status"] not in APPROVAL_STATUSES:
        raise ValueError(f"invalid approval status: {data['status']}")
    _require_str(data, "requested_by")
    _require_str(data, "risk_tier")
    _require_str(data, "created_utc")
    _require_str(data, "updated_utc")
    if not isinstance(data.get("metadata"), dict):
        raise ValueError("approval metadata must be an object")


def validate_consensus_record_dict(data: dict[str, Any]) -> None:
    if not isinstance(data, dict):
        raise ValueError("consensus record must be an object")
    _require_str(data, "consensus_id")
    _require_str(data, "mission_id")
    _require_str(data, "consensus_type")
    if data["consensus_type"] not in CONSENSUS_TYPES:
        raise ValueError(f"invalid consensus type: {data['consensus_type']}")
    _require_str(data, "decision")
    if data["decision"] not in CONSENSUS_DECISIONS:
        raise ValueError(f"invalid consensus decision: {data['decision']}")
    _require_str(data, "actor")
    _require_str(data, "created_utc")
    if not isinstance(data.get("metadata"), dict):
        raise ValueError("consensus metadata must be an object")


def _transition_approval(
    record: ApprovalRecord | dict[str, Any],
    *,
    action: ApprovalAction,
    status: ApprovalStatus,
    reviewed_by: str | None,
    reason: str | None,
) -> ApprovalRecord:
    current = ApprovalRecord.from_dict(record) if isinstance(record, dict) else record
    current.action = action
    current.status = status
    current.reviewed_by = reviewed_by or current.reviewed_by
    if reason is not None:
        current.reason = reason
    current.updated_utc = utc_now()
    validate_approval_record_dict(current.to_dict())
    return current


def _normalize_repositories(
    *,
    target_repository: str | None,
    target_repositories: list[str] | None,
) -> list[str]:
    raw: list[str] = []
    if isinstance(target_repositories, list):
        raw.extend(str(item).strip() for item in target_repositories if isinstance(item, str) and item.strip())
    if isinstance(target_repository, str) and target_repository.strip():
        raw.insert(0, target_repository.strip())
    out: list[str] = []
    seen: set[str] = set()
    for repo in raw:
        if repo in seen:
            continue
        seen.add(repo)
        out.append(repo)
    return out


def _require_str(data: dict[str, Any], key: str) -> None:
    if not isinstance(data.get(key), str) or not str(data.get(key)).strip():
        raise ValueError(f"mission/task field {key!r} must be a non-empty string")


def _require_list(data: dict[str, Any], key: str) -> None:
    if not isinstance(data.get(key), list):
        raise ValueError(f"mission/task field {key!r} must be a list")


def _optional_str(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str)]


def _dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def _int_value(value: Any, *, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except Exception:
        return default
