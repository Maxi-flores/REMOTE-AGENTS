from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional


RepositoryStatus = Literal["active", "pending", "archived", "disabled", "unknown"]
RiskTier = Literal["low", "medium", "high", "critical"]
HealthStatus = Literal["healthy", "warning", "degraded", "failing", "unknown"]
AuditDecision = Literal["allowed", "denied", "needs_approval", "needs_review", "unknown"]


REPOSITORY_STATUSES = {"active", "pending", "archived", "disabled", "unknown"}
ALLOWED_OPERATIONS = {
    "read",
    "write",
    "test",
    "build",
    "lint",
    "typecheck",
    "deploy",
    "network_fetch",
    "mcp_tool_call",
    "shell_command",
    "git_status",
    "git_diff",
    "git_commit",
    "git_push",
}
RISK_TIERS = {"low", "medium", "high", "critical"}
HEALTH_STATUSES = {"healthy", "warning", "degraded", "failing", "unknown"}
AUDIT_DECISIONS = {"allowed", "denied", "needs_approval", "needs_review", "unknown"}


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


@dataclass
class RepositoryGovernanceProfile:
    repository_name: str
    repository_group: str
    repository_category: str
    status: RepositoryStatus
    primary_agent_class: Optional[str] = None
    twin_agent_class: Optional[str] = None
    allowed_operations: List[str] = field(default_factory=list)
    denied_operations: List[str] = field(default_factory=list)
    required_checks: List[str] = field(default_factory=list)
    risk_tier: RiskTier = "medium"
    default_branch: str = "main"
    workspace_path: Optional[str] = None
    deployment_targets: List[str] = field(default_factory=list)
    secrets_policy: Dict[str, Any] = field(default_factory=dict)
    network_policy: Dict[str, Any] = field(default_factory=dict)
    write_policy: Dict[str, Any] = field(default_factory=dict)
    approval_policy: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_utc: str = field(default_factory=utc_now)
    updated_utc: str = field(default_factory=utc_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "repository_name": self.repository_name,
            "repository_group": self.repository_group,
            "repository_category": self.repository_category,
            "status": self.status,
            "primary_agent_class": self.primary_agent_class,
            "twin_agent_class": self.twin_agent_class,
            "allowed_operations": list(self.allowed_operations),
            "denied_operations": list(self.denied_operations),
            "required_checks": list(self.required_checks),
            "risk_tier": self.risk_tier,
            "default_branch": self.default_branch,
            "workspace_path": self.workspace_path,
            "deployment_targets": list(self.deployment_targets),
            "secrets_policy": dict(self.secrets_policy),
            "network_policy": dict(self.network_policy),
            "write_policy": dict(self.write_policy),
            "approval_policy": dict(self.approval_policy),
            "metadata": dict(self.metadata),
            "created_utc": self.created_utc,
            "updated_utc": self.updated_utc,
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "RepositoryGovernanceProfile":
        validate_governance_profile_dict(payload)
        return cls(
            repository_name=payload["repository_name"],
            repository_group=payload["repository_group"],
            repository_category=str(payload.get("repository_category") or "unknown"),
            status=payload["status"],
            primary_agent_class=_optional_str(payload.get("primary_agent_class")),
            twin_agent_class=_optional_str(payload.get("twin_agent_class")),
            allowed_operations=_str_list(payload.get("allowed_operations")),
            denied_operations=_str_list(payload.get("denied_operations")),
            required_checks=_str_list(payload.get("required_checks")),
            risk_tier=payload["risk_tier"],
            default_branch=str(payload.get("default_branch") or "main"),
            workspace_path=_optional_str(payload.get("workspace_path")),
            deployment_targets=_str_list(payload.get("deployment_targets")),
            secrets_policy=dict(payload.get("secrets_policy") or {}),
            network_policy=dict(payload.get("network_policy") or {}),
            write_policy=dict(payload.get("write_policy") or {}),
            approval_policy=dict(payload.get("approval_policy") or {}),
            metadata=dict(payload.get("metadata") or {}),
            created_utc=str(payload.get("created_utc") or utc_now()),
            updated_utc=str(payload.get("updated_utc") or utc_now()),
        )


@dataclass
class RepositoryHealthSnapshot:
    snapshot_id: str
    repository_name: str
    status: HealthStatus
    checked_utc: str
    branch: Optional[str] = None
    working_tree_state: Optional[str] = None
    build_status: Optional[str] = None
    lint_status: Optional[str] = None
    test_status: Optional[str] = None
    typecheck_status: Optional[str] = None
    known_risks: List[str] = field(default_factory=list)
    missing_contracts: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "repository_name": self.repository_name,
            "status": self.status,
            "checked_utc": self.checked_utc,
            "branch": self.branch,
            "working_tree_state": self.working_tree_state,
            "build_status": self.build_status,
            "lint_status": self.lint_status,
            "test_status": self.test_status,
            "typecheck_status": self.typecheck_status,
            "known_risks": list(self.known_risks),
            "missing_contracts": list(self.missing_contracts),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "RepositoryHealthSnapshot":
        validate_health_snapshot_dict(payload)
        return cls(
            snapshot_id=payload["snapshot_id"],
            repository_name=payload["repository_name"],
            status=payload["status"],
            checked_utc=payload["checked_utc"],
            branch=_optional_str(payload.get("branch")),
            working_tree_state=_optional_str(payload.get("working_tree_state")),
            build_status=_optional_str(payload.get("build_status")),
            lint_status=_optional_str(payload.get("lint_status")),
            test_status=_optional_str(payload.get("test_status")),
            typecheck_status=_optional_str(payload.get("typecheck_status")),
            known_risks=_str_list(payload.get("known_risks")),
            missing_contracts=_str_list(payload.get("missing_contracts")),
            warnings=_str_list(payload.get("warnings")),
            errors=_str_list(payload.get("errors")),
            metadata=dict(payload.get("metadata") or {}),
        )


@dataclass
class RepositoryAuditRecord:
    audit_id: str
    repository_name: str
    actor: str
    action: str
    operation: str
    decision: AuditDecision
    risk_tier: RiskTier
    created_utc: str
    mission_id: Optional[str] = None
    task_id: Optional[str] = None
    reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "audit_id": self.audit_id,
            "repository_name": self.repository_name,
            "mission_id": self.mission_id,
            "task_id": self.task_id,
            "actor": self.actor,
            "action": self.action,
            "operation": self.operation,
            "decision": self.decision,
            "risk_tier": self.risk_tier,
            "reason": self.reason,
            "created_utc": self.created_utc,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "RepositoryAuditRecord":
        validate_audit_record_dict(payload)
        return cls(
            audit_id=payload["audit_id"],
            repository_name=payload["repository_name"],
            mission_id=_optional_str(payload.get("mission_id")),
            task_id=_optional_str(payload.get("task_id")),
            actor=payload["actor"],
            action=payload["action"],
            operation=payload["operation"],
            decision=payload["decision"],
            risk_tier=payload["risk_tier"],
            reason=_optional_str(payload.get("reason")),
            created_utc=payload["created_utc"],
            metadata=dict(payload.get("metadata") or {}),
        )


def create_governance_profile(
    *,
    repository_name: str,
    repository_group: str,
    repository_category: str = "unknown",
    status: RepositoryStatus = "unknown",
    risk_tier: RiskTier = "medium",
    **kwargs: Any,
) -> RepositoryGovernanceProfile:
    profile = RepositoryGovernanceProfile(
        repository_name=repository_name,
        repository_group=repository_group,
        repository_category=repository_category,
        status=status,
        risk_tier=risk_tier,
        **kwargs,
    )
    validate_governance_profile_dict(profile.to_dict())
    return profile


def create_health_snapshot(
    *,
    repository_name: str,
    status: HealthStatus = "unknown",
    snapshot_id: Optional[str] = None,
    **kwargs: Any,
) -> RepositoryHealthSnapshot:
    snapshot = RepositoryHealthSnapshot(
        snapshot_id=snapshot_id or new_id("health"),
        repository_name=repository_name,
        status=status,
        checked_utc=kwargs.pop("checked_utc", utc_now()),
        **kwargs,
    )
    validate_health_snapshot_dict(snapshot.to_dict())
    return snapshot


def create_audit_record(
    *,
    repository_name: str,
    actor: str,
    action: str,
    operation: str,
    decision: AuditDecision,
    risk_tier: RiskTier,
    audit_id: Optional[str] = None,
    **kwargs: Any,
) -> RepositoryAuditRecord:
    record = RepositoryAuditRecord(
        audit_id=audit_id or new_id("repo_audit"),
        repository_name=repository_name,
        actor=actor,
        action=action,
        operation=operation,
        decision=decision,
        risk_tier=risk_tier,
        created_utc=kwargs.pop("created_utc", utc_now()),
        **kwargs,
    )
    validate_audit_record_dict(record.to_dict())
    return record


def validate_governance_profile_dict(payload: Dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ValueError("governance profile must be an object")
    _require_str(payload, "repository_name")
    _require_str(payload, "repository_group")
    status = _require_str(payload, "status")
    if status not in REPOSITORY_STATUSES:
        raise ValueError(f"invalid repository status: {status}")
    risk_tier = _require_str(payload, "risk_tier")
    if risk_tier not in RISK_TIERS:
        raise ValueError(f"invalid risk tier: {risk_tier}")
    for key in ("allowed_operations", "denied_operations", "required_checks"):
        _require_list(payload, key)
    for operation in _str_list(payload.get("allowed_operations")) + _str_list(payload.get("denied_operations")):
        if operation not in ALLOWED_OPERATIONS:
            raise ValueError(f"invalid repository operation: {operation}")
    for key in ("secrets_policy", "network_policy", "write_policy", "approval_policy", "metadata"):
        if not isinstance(payload.get(key), dict):
            raise ValueError(f"{key} must be an object")
    _require_str(payload, "created_utc")
    _require_str(payload, "updated_utc")


def validate_health_snapshot_dict(payload: Dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ValueError("health snapshot must be an object")
    _require_str(payload, "snapshot_id")
    _require_str(payload, "repository_name")
    status = _require_str(payload, "status")
    if status not in HEALTH_STATUSES:
        raise ValueError(f"invalid health status: {status}")
    _require_str(payload, "checked_utc")
    for key in ("known_risks", "missing_contracts", "warnings", "errors"):
        _require_list(payload, key)
    if not isinstance(payload.get("metadata"), dict):
        raise ValueError("metadata must be an object")


def validate_audit_record_dict(payload: Dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ValueError("audit record must be an object")
    _require_str(payload, "audit_id")
    _require_str(payload, "repository_name")
    _require_str(payload, "actor")
    _require_str(payload, "action")
    _require_str(payload, "operation")
    decision = _require_str(payload, "decision")
    if decision not in AUDIT_DECISIONS:
        raise ValueError(f"invalid audit decision: {decision}")
    risk_tier = _require_str(payload, "risk_tier")
    if risk_tier not in RISK_TIERS:
        raise ValueError(f"invalid risk tier: {risk_tier}")
    _require_str(payload, "created_utc")
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


def _str_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str)]
