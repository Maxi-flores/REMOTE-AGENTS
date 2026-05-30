from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from tool_router.contracts import ToolRoute


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_tool_route_audit_record(
    route: ToolRoute,
    requested_by: str,
    repository_name: Optional[str] = None,
    mission_id: Optional[str] = None,
    task_id: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "audit_id": f"tool_audit_{uuid4().hex}",
        "tool_name": route.tool_name,
        "provider": route.provider,
        "risk_tier": route.risk_tier,
        "approval_required": route.approval_required,
        "repository_name": repository_name,
        "mission_id": mission_id,
        "task_id": task_id,
        "requested_by": requested_by,
        "created_utc": utc_now(),
        "metadata": {
            "implementation_status": route.implementation_status,
            "network_access": route.network_access,
            "write_access": route.write_access,
            "audit_required": route.audit_required,
        },
    }
