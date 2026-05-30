from __future__ import annotations

from typing import List, Optional

from tool_router.contracts import ToolRoute


def requires_human_approval(route: ToolRoute) -> bool:
    return route.approval_required or route.risk_tier in {"critical"}


def is_network_denied_by_default(route: ToolRoute) -> bool:
    if not route.network_access:
        return False
    return not bool(route.metadata.get("network_explicitly_allowed"))


def requires_write_approval(route: ToolRoute) -> bool:
    return route.write_access or route.approval_required


def requires_path_traversal_protection(route: ToolRoute) -> bool:
    return route.requires_path_safety or route.requires_repo_boundary


def is_allowed_for_repository_group(route: ToolRoute, group: Optional[str]) -> bool:
    if not group:
        return True
    if group in route.denied_repository_groups:
        return False
    if route.allowed_repository_groups and group not in route.allowed_repository_groups:
        return False
    return True


def is_allowed_in_runtime_context(route: ToolRoute, context: Optional[str]) -> bool:
    if not context:
        return True
    if route.allowed_runtime_contexts and context not in route.allowed_runtime_contexts:
        return False
    return True


def explain_tool_policy(route: ToolRoute) -> List[str]:
    notes: List[str] = []
    if route.implementation_status == "disabled":
        notes.append("tool disabled")
    if requires_human_approval(route):
        notes.append("human approval required before future enforcement")
    if is_network_denied_by_default(route):
        notes.append("network access denied by default")
    if route.write_access:
        notes.append("write-capable tool requires approval")
    if requires_path_traversal_protection(route):
        notes.append("repo boundary and path traversal protection required")
    if route.audit_required:
        notes.append("audit record recommended")
    if not notes:
        notes.append("read-only/no-network diagnostic route preferred")
    return notes
