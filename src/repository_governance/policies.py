from __future__ import annotations

from typing import Any, Dict, Optional

from repository_governance.contracts import (
    ALLOWED_OPERATIONS,
    RepositoryAuditRecord,
    RepositoryGovernanceProfile,
    create_audit_record,
)


SAFE_READ_OPERATIONS = {"read", "git_status", "git_diff"}
APPROVAL_REQUIRED_OPERATIONS = {
    "write",
    "git_commit",
    "git_push",
    "deploy",
    "network_fetch",
    "shell_command",
}


def is_operation_allowed(profile: RepositoryGovernanceProfile | Dict[str, Any], operation: str) -> bool:
    payload = _profile_dict(profile)
    if operation in payload.get("denied_operations", []):
        return False
    if operation in payload.get("allowed_operations", []):
        return True
    return operation in SAFE_READ_OPERATIONS


def requires_approval(profile: RepositoryGovernanceProfile | Dict[str, Any], operation: str) -> bool:
    payload = _profile_dict(profile)
    if operation in payload.get("denied_operations", []):
        return False
    approval_policy = payload.get("approval_policy") if isinstance(payload.get("approval_policy"), dict) else {}
    required_ops = approval_policy.get("required_for_operations")
    if isinstance(required_ops, list) and operation in required_ops:
        return True
    if operation in APPROVAL_REQUIRED_OPERATIONS:
        return True
    required_tiers = approval_policy.get("required_for_risk_tiers")
    risk_tier = payload.get("risk_tier")
    if isinstance(required_tiers, list) and risk_tier in required_tiers:
        return operation not in SAFE_READ_OPERATIONS
    return False


def evaluate_repository_operation(
    profile: RepositoryGovernanceProfile | Dict[str, Any],
    operation: str,
    actor: str,
    mission_id: Optional[str] = None,
    task_id: Optional[str] = None,
) -> RepositoryAuditRecord:
    payload = _profile_dict(profile)
    if operation not in ALLOWED_OPERATIONS:
        decision = "needs_review"
        reason = "unknown_operation"
    elif operation in payload.get("denied_operations", []):
        decision = "denied"
        reason = "operation_explicitly_denied"
    elif requires_approval(payload, operation):
        decision = "needs_approval"
        reason = "operation_requires_approval"
    elif is_operation_allowed(payload, operation):
        decision = "allowed"
        reason = "operation_allowed_by_policy"
    else:
        decision = "needs_review"
        reason = "operation_not_explicitly_allowed"

    return create_audit_record(
        repository_name=payload["repository_name"],
        mission_id=mission_id,
        task_id=task_id,
        actor=actor,
        action=f"evaluate:{operation}",
        operation=operation,
        decision=decision,  # type: ignore[arg-type]
        risk_tier=payload["risk_tier"],
        reason=reason,
        metadata={
            "repository_group": payload.get("repository_group"),
            "policy_enforced": False,
        },
    )


def explain_governance_decision(record: RepositoryAuditRecord | Dict[str, Any]) -> str:
    payload = record.to_dict() if isinstance(record, RepositoryAuditRecord) else dict(record)
    decision = payload.get("decision", "unknown")
    operation = payload.get("operation", "unknown")
    repository = payload.get("repository_name", "unknown")
    reason = payload.get("reason") or "no reason provided"
    return f"{decision}: {operation} on {repository} ({reason})"


def _profile_dict(profile: RepositoryGovernanceProfile | Dict[str, Any]) -> Dict[str, Any]:
    return profile.to_dict() if isinstance(profile, RepositoryGovernanceProfile) else dict(profile)
