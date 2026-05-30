from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from tool_router.contracts import ToolRoute, create_disabled_fallback_route


REPO_ROOT = Path(__file__).resolve().parents[2]
CANONICAL_TOOLS_PATH = REPO_ROOT / "config" / "registries" / "tools.json"
LEGACY_TOOLS_PATH = REPO_ROOT / "config" / "platform_mcp_tools.json"


def load_canonical_tool_registry(path: Optional[Path] = None) -> Dict[str, Any]:
    return _load_json_object(path or CANONICAL_TOOLS_PATH)


def load_legacy_platform_tools(path: Optional[Path] = None) -> Dict[str, Any]:
    return _load_json_object(path or LEGACY_TOOLS_PATH)


def resolve_tool_route(
    tool_name: str,
    repository_group: Optional[str] = None,
    runtime_context: Optional[str] = None,
) -> ToolRoute:
    routes = _build_routes_by_name()
    route = routes.get(tool_name)
    if route is None:
        return create_disabled_fallback_route(tool_name)
    if repository_group and repository_group in route.denied_repository_groups:
        blocked = route.to_dict()
        blocked["implementation_status"] = "disabled"
        blocked["approval_required"] = True
        blocked["metadata"] = {
            **blocked.get("metadata", {}),
            "disabled_reason": "repository_group_denied",
            "repository_group": repository_group,
        }
        return ToolRoute.from_dict(blocked)
    if runtime_context and route.allowed_runtime_contexts and runtime_context not in route.allowed_runtime_contexts:
        blocked = route.to_dict()
        blocked["implementation_status"] = "disabled"
        blocked["approval_required"] = True
        blocked["metadata"] = {
            **blocked.get("metadata", {}),
            "disabled_reason": "runtime_context_not_allowed",
            "runtime_context": runtime_context,
        }
        return ToolRoute.from_dict(blocked)
    return route


def list_tool_routes() -> List[ToolRoute]:
    return sorted(_build_routes_by_name().values(), key=lambda route: route.tool_name)


def tool_exists(tool_name: str) -> bool:
    return resolve_tool_route(tool_name).implementation_status != "disabled"


def _build_routes_by_name() -> Dict[str, ToolRoute]:
    canonical = load_canonical_tool_registry()
    legacy = load_legacy_platform_tools()
    canonical_by_name = _tools_by_name(canonical)
    legacy_by_name = _tools_by_name(legacy)

    routes: Dict[str, ToolRoute] = {}
    for name in sorted(set(canonical_by_name) | set(legacy_by_name)):
        canonical_tool = canonical_by_name.get(name, {})
        legacy_tool = legacy_by_name.get(name, {})
        routes[name] = _merge_tool_route(name, canonical_tool, legacy_tool)
    return routes


def _merge_tool_route(name: str, canonical: Dict[str, Any], legacy: Dict[str, Any]) -> ToolRoute:
    description = str(canonical.get("description") or legacy.get("description") or "")
    approval_requirements = canonical.get("approval_requirements") or []
    runtime_contexts = canonical.get("allowed_runtime_context") or canonical.get("allowed_runtime_contexts") or []
    status = _normalize_status(canonical.get("current_implementation_status"))
    risk_tier = str(canonical.get("risk_tier") or _infer_risk_tier(name, description))
    provider = str(canonical.get("provider") or _infer_provider(name, description))
    network_access = bool(canonical.get("network_access", _infer_network_access(name, description)))
    write_access = bool(canonical.get("write_access", _infer_write_access(name, description)))
    requires_repo_boundary = bool(
        canonical.get("requires_repo_boundary", _infer_requires_repo_boundary(name, description))
    )
    requires_path_safety = bool(
        canonical.get("requires_path_safety", requires_repo_boundary or "path traversal" in description.lower())
    )
    approval_required = bool(canonical.get("approval_required", bool(approval_requirements) or write_access))

    payload = {
        "tool_name": name,
        "provider": provider,
        "implementation_status": status,
        "risk_tier": risk_tier if risk_tier in {"low", "medium", "high", "critical"} else "high",
        "approval_required": approval_required,
        "allowed_runtime_contexts": list(runtime_contexts) if isinstance(runtime_contexts, list) else [],
        "allowed_repository_groups": list(canonical.get("allowed_repository_groups") or []),
        "denied_repository_groups": list(canonical.get("denied_repository_groups") or []),
        "requires_repo_boundary": requires_repo_boundary,
        "requires_path_safety": requires_path_safety,
        "network_access": network_access,
        "write_access": write_access,
        "audit_required": bool(canonical.get("audit_required", risk_tier in {"high", "critical"} or approval_required)),
        "metadata": {
            "description": description,
            "approval_requirements": list(approval_requirements) if isinstance(approval_requirements, list) else [],
            "legacy_schema_present": bool(legacy),
            "legacy_arguments": legacy.get("arguments") if isinstance(legacy.get("arguments"), dict) else {},
            "canonical_present": bool(canonical),
        },
    }
    return ToolRoute.from_dict(payload)


def _load_json_object(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"schema_version": 1, "tools": []}
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        return {"schema_version": 1, "tools": []}
    return payload


def _tools_by_name(registry: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    tools = registry.get("tools") or []
    if not isinstance(tools, list):
        return {}
    result: Dict[str, Dict[str, Any]] = {}
    for tool in tools:
        if not isinstance(tool, dict):
            continue
        name = tool.get("name") or tool.get("tool_name")
        if isinstance(name, str) and name.strip():
            result[name] = tool
    return result


def _normalize_status(value: Any) -> str:
    raw = str(value or "active").lower()
    if raw in {"implemented", "implemented_but_restricted", "active"}:
        return "active"
    if raw in {"planned", "disabled", "deprecated"}:
        return raw
    return "planned"


def _infer_provider(name: str, description: str) -> str:
    lowered = f"{name} {description}".lower()
    if "ollama" in lowered:
        return "ollama"
    if "codex" in lowered:
        return "codex"
    if "claude" in lowered:
        return "claude_code"
    if "browser" in lowered:
        return "browser"
    if "http" in lowered or "network" in lowered:
        return "external_api"
    if "command" in lowered or "execute" in lowered or "run " in lowered:
        return "shell"
    return "mcp"


def _infer_risk_tier(name: str, description: str) -> str:
    lowered = f"{name} {description}".lower()
    if "write" in lowered or "execute" in lowered or "network" in lowered:
        return "high"
    if "run " in lowered or "command" in lowered:
        return "medium"
    return "low"


def _infer_network_access(name: str, description: str) -> bool:
    lowered = f"{name} {description}".lower()
    return "network" in lowered or "http" in lowered or "url" in lowered


def _infer_write_access(name: str, description: str) -> bool:
    lowered = f"{name} {description}".lower()
    return "write" in lowered or "writes" in lowered or "execute" in lowered or "run " in lowered


def _infer_requires_repo_boundary(name: str, description: str) -> bool:
    lowered = f"{name} {description}".lower()
    return "repo" in lowered or "workspace" in lowered or "path" in lowered or "asset" in lowered
