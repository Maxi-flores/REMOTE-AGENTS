from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tools.logger import log_engine_interruption


DEFAULT_REGISTRY_PATH = Path("config/agent_registry.json")


@dataclass(frozen=True, slots=True)
class RepoGovernanceRoute:
    target_repository: str | None
    resolved_repository: str | None
    used_default_profile: bool
    primary_agent_class: str
    twin_agent_class: str
    execution_constraints: dict[str, Any]
    quantization_preference: str | None = None
    reason: str | None = None


_REGISTRY_CACHE: dict[str, Any] | None = None
_REGISTRY_CACHE_MTIME: float | None = None


def _safe_int(value: Any, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    try:
        return int(value)
    except Exception:
        return default


def _load_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_agent_registry(path: Path | str = DEFAULT_REGISTRY_PATH, *, use_cache: bool = True) -> dict[str, Any]:
    global _REGISTRY_CACHE, _REGISTRY_CACHE_MTIME

    p = Path(path)
    try:
        st = p.stat()
    except FileNotFoundError:
        return {}
    except OSError:
        return {}

    mtime = float(st.st_mtime)
    if use_cache and _REGISTRY_CACHE is not None and _REGISTRY_CACHE_MTIME == mtime:
        return _REGISTRY_CACHE

    try:
        loaded = _load_json(p)
    except Exception:
        loaded = {}

    registry: dict[str, Any] = loaded if isinstance(loaded, dict) else {}
    _REGISTRY_CACHE = registry
    _REGISTRY_CACHE_MTIME = mtime
    return registry


def extract_target_repository(task_payload: dict[str, Any]) -> str | None:
    value = task_payload.get("target_repository")
    if isinstance(value, str):
        value = value.strip()
        if value:
            return value

    # Allow the orchestrator pipeline to pass multiple repositories.
    targets = task_payload.get("target_repositories")
    if isinstance(targets, list) and targets:
        first = targets[0]
        if isinstance(first, str) and first.strip():
            return first.strip()
    return None


def _default_profile(registry: dict[str, Any]) -> dict[str, Any]:
    dp = registry.get("default_profile")
    return dp if isinstance(dp, dict) else {}


def _repo_profiles(registry: dict[str, Any]) -> dict[str, Any]:
    repos = registry.get("repositories")
    if isinstance(repos, dict):
        return repos
    # Back-compat: allow a flat mapping at the top-level.
    return registry


def _profile_has_required_fields(profile: dict[str, Any]) -> bool:
    return (
        isinstance(profile.get("primary_agent_class"), str)
        and isinstance(profile.get("twin_agent_class"), str)
        and isinstance(profile.get("execution_constraints"), dict)
    )


def resolve_repo_governance_route(
    task_payload: dict[str, Any],
    *,
    registry_path: Path | str = DEFAULT_REGISTRY_PATH,
) -> RepoGovernanceRoute:
    registry = load_agent_registry(registry_path)
    target = extract_target_repository(task_payload)

    repos = _repo_profiles(registry)
    default_profile = _default_profile(registry)

    resolved_profile: dict[str, Any] | None = None
    resolved_repo: str | None = None
    reason: str | None = None
    used_default = False

    if target and isinstance(repos, dict):
        candidate = repos.get(target)
        if isinstance(candidate, dict):
            resolved_profile = candidate
            resolved_repo = target

    routing_cfg = resolved_profile.get("routing") if isinstance(resolved_profile, dict) else None
    routing_enabled = True
    if isinstance(routing_cfg, dict) and routing_cfg.get("enabled") is False:
        routing_enabled = False
        reason = str(routing_cfg.get("reason") or "routing disabled for repository")

    if not target:
        used_default = True
        reason = "missing target_repository"
    elif resolved_profile is None:
        used_default = True
        reason = f"unknown repository: {target}"
    elif not routing_enabled:
        used_default = True
        reason = f"unmapped repository: {target}"
    elif not _profile_has_required_fields(resolved_profile):
        used_default = True
        reason = f"incomplete agent profile for repository: {target}"

    profile = default_profile if used_default else (resolved_profile or default_profile)
    if not isinstance(profile, dict):
        profile = {}

    primary = profile.get("primary_agent_class")
    twin = profile.get("twin_agent_class")
    constraints = profile.get("execution_constraints")
    quant = None

    if isinstance(constraints, dict):
        quant = constraints.get("quantization_preference")

    if not isinstance(primary, str) or not primary.strip():
        primary = "RuntimeDiagnosticAgent"
    if not isinstance(twin, str) or not twin.strip():
        twin = "RuntimeDiagnosticTwinAgent"
    if not isinstance(constraints, dict):
        constraints = {"num_thread": 4, "quantization_preference": "Q5_K_M", "max_context_chars": 12000}

    if used_default:
        log_engine_interruption(
            event_type="REPO_ROUTER_FALLBACK",
            message=f"Falling back to default agent profile ({reason}).",
            details={
                "target_repository": target,
                "resolved_repository": resolved_repo,
                "reason": reason,
                "registry_path": str(registry_path),
            },
        )

    return RepoGovernanceRoute(
        target_repository=target,
        resolved_repository=resolved_repo if not used_default else None,
        used_default_profile=used_default,
        primary_agent_class=str(primary),
        twin_agent_class=str(twin),
        execution_constraints=dict(constraints),
        quantization_preference=str(quant) if isinstance(quant, str) else None,
        reason=reason,
    )


def build_governance_system_context(route: RepoGovernanceRoute) -> str:
    constraints = route.execution_constraints or {}
    num_thread = _safe_int(constraints.get("num_thread"), 4)
    max_context_chars = _safe_int(constraints.get("max_context_chars"), 12000)
    quant = route.quantization_preference or str(constraints.get("quantization_preference") or "")

    repo_label = route.target_repository or route.resolved_repository or "unknown"
    resolved_label = route.resolved_repository or "default"
    reason = route.reason or ("default profile" if route.used_default_profile else "matched profile")

    # Keep this short: it counts against the context window.
    lines = [
        "[GOVERNANCE_ROUTER]",
        f"target_repository={repo_label}",
        f"resolved_repository={resolved_label}",
        f"primary_agent_class={route.primary_agent_class}",
        f"twin_agent_class={route.twin_agent_class}",
        f"num_thread={num_thread}",
        f"max_context_chars={max_context_chars}",
    ]
    if quant:
        lines.append(f"quantization_preference={quant}")
    lines.append(f"routing_reason={reason}")
    lines.append(
        "Instruction: apply paired governance; primary proposes changes, twin audits and enforces constraints."
    )
    return "\n".join(lines)


def constraints_for_engine(route: RepoGovernanceRoute) -> tuple[int, int]:
    constraints = route.execution_constraints or {}
    num_thread = _safe_int(constraints.get("num_thread"), 4)
    max_context_chars = _safe_int(constraints.get("max_context_chars"), 12000)
    return num_thread, max_context_chars
