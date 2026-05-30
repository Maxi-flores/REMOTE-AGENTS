from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal


ToolProvider = Literal[
    "local_builtin",
    "mcp",
    "shell",
    "ollama",
    "codex",
    "claude_code",
    "browser",
    "external_api",
    "future_cloud",
]

ImplementationStatus = Literal["active", "planned", "disabled", "deprecated"]
RiskTier = Literal["low", "medium", "high", "critical"]


TOOL_PROVIDERS = {
    "local_builtin",
    "mcp",
    "shell",
    "ollama",
    "codex",
    "claude_code",
    "browser",
    "external_api",
    "future_cloud",
}
IMPLEMENTATION_STATUSES = {"active", "planned", "disabled", "deprecated"}
RISK_TIERS = {"low", "medium", "high", "critical"}


@dataclass
class ToolRoute:
    tool_name: str
    provider: ToolProvider
    implementation_status: ImplementationStatus
    risk_tier: RiskTier
    approval_required: bool
    allowed_runtime_contexts: List[str] = field(default_factory=list)
    allowed_repository_groups: List[str] = field(default_factory=list)
    denied_repository_groups: List[str] = field(default_factory=list)
    requires_repo_boundary: bool = True
    requires_path_safety: bool = True
    network_access: bool = False
    write_access: bool = False
    audit_required: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "provider": self.provider,
            "implementation_status": self.implementation_status,
            "risk_tier": self.risk_tier,
            "approval_required": self.approval_required,
            "allowed_runtime_contexts": list(self.allowed_runtime_contexts),
            "allowed_repository_groups": list(self.allowed_repository_groups),
            "denied_repository_groups": list(self.denied_repository_groups),
            "requires_repo_boundary": self.requires_repo_boundary,
            "requires_path_safety": self.requires_path_safety,
            "network_access": self.network_access,
            "write_access": self.write_access,
            "audit_required": self.audit_required,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "ToolRoute":
        validate_tool_route_dict(payload)
        return cls(
            tool_name=payload["tool_name"],
            provider=payload["provider"],
            implementation_status=payload["implementation_status"],
            risk_tier=payload["risk_tier"],
            approval_required=payload["approval_required"],
            allowed_runtime_contexts=list(payload.get("allowed_runtime_contexts") or []),
            allowed_repository_groups=list(payload.get("allowed_repository_groups") or []),
            denied_repository_groups=list(payload.get("denied_repository_groups") or []),
            requires_repo_boundary=bool(payload.get("requires_repo_boundary", True)),
            requires_path_safety=bool(payload.get("requires_path_safety", True)),
            network_access=bool(payload.get("network_access", False)),
            write_access=bool(payload.get("write_access", False)),
            audit_required=bool(payload.get("audit_required", True)),
            metadata=dict(payload.get("metadata") or {}),
        )


def create_disabled_fallback_route(tool_name: str) -> ToolRoute:
    name = tool_name.strip() if isinstance(tool_name, str) and tool_name.strip() else "unknown"
    return ToolRoute(
        tool_name=name,
        provider="local_builtin",
        implementation_status="disabled",
        risk_tier="high",
        approval_required=True,
        allowed_runtime_contexts=[],
        allowed_repository_groups=[],
        denied_repository_groups=[],
        requires_repo_boundary=True,
        requires_path_safety=True,
        network_access=False,
        write_access=False,
        audit_required=True,
        metadata={"fallback_reason": "unknown_or_unavailable_tool"},
    )


def validate_tool_route_dict(payload: Dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ValueError("ToolRoute payload must be an object")
    _require_str(payload, "tool_name")
    provider = _require_str(payload, "provider")
    if provider not in TOOL_PROVIDERS:
        raise ValueError(f"Invalid tool provider: {provider}")
    status = _require_str(payload, "implementation_status")
    if status not in IMPLEMENTATION_STATUSES:
        raise ValueError(f"Invalid implementation status: {status}")
    risk_tier = _require_str(payload, "risk_tier")
    if risk_tier not in RISK_TIERS:
        raise ValueError(f"Invalid risk tier: {risk_tier}")
    if not isinstance(payload.get("approval_required"), bool):
        raise ValueError("approval_required must be bool")
    if not isinstance(payload.get("allowed_runtime_contexts", []), list):
        raise ValueError("allowed_runtime_contexts must be list")
    if not isinstance(payload.get("allowed_repository_groups", []), list):
        raise ValueError("allowed_repository_groups must be list")
    if not isinstance(payload.get("denied_repository_groups", []), list):
        raise ValueError("denied_repository_groups must be list")
    for key in (
        "requires_repo_boundary",
        "requires_path_safety",
        "network_access",
        "write_access",
        "audit_required",
    ):
        if key in payload and not isinstance(payload[key], bool):
            raise ValueError(f"{key} must be bool")
    if not isinstance(payload.get("metadata", {}), dict):
        raise ValueError("metadata must be object")


def _require_str(payload: Dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} is required")
    return value
