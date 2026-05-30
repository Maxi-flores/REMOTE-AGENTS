from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from repository_governance.contracts import RepositoryGovernanceProfile, create_governance_profile


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPOSITORIES_REGISTRY = REPO_ROOT / "config" / "registries" / "repositories.json"


def profile_from_repository_registry_record(record: Dict[str, Any]) -> RepositoryGovernanceProfile:
    name = str(record.get("name") or record.get("repository_name") or "").strip()
    group = str(record.get("group") or record.get("repository_group") or "unknown").strip()
    category = str(record.get("category") or record.get("repository_category") or "unknown").strip()
    source_status = str(record.get("status") or "unknown")
    health_indicators = _str_list(record.get("structural_health_indicators"))
    risk_tier = _infer_risk_tier(health_indicators)
    profile = create_governance_profile(
        repository_name=name,
        repository_group=group,
        repository_category=category,
        status=_normalize_status(source_status),
        primary_agent_class=_optional_str(record.get("primary_agent_class")),
        twin_agent_class=_optional_str(record.get("twin_agent_class")),
        allowed_operations=["read", "git_status", "git_diff"],
        denied_operations=[],
        required_checks=_infer_required_checks(health_indicators),
        risk_tier=risk_tier,
        default_branch="main",
        deployment_targets=[],
        secrets_policy={
            "default": "deny_secret_exposure",
            "requires_review": any(_mentions_secret(indicator) for indicator in health_indicators),
        },
        network_policy={"default": "deny", "requires_approval": True},
        write_policy={"default": "approval_required", "requires_path_safety": True},
        approval_policy={
            "required_for_operations": [
                "write",
                "git_commit",
                "git_push",
                "deploy",
                "network_fetch",
                "shell_command",
            ],
            "required_for_risk_tiers": ["high", "critical"],
        },
        metadata={
            "source": "config/registries/repositories.json",
            "source_status": source_status,
            "detected_class": record.get("detected_class"),
            "core_objective": record.get("core_objective"),
            "structural_health_indicators": health_indicators,
        },
    )
    return profile


def import_profiles_from_repositories_registry(
    path: str | Path = DEFAULT_REPOSITORIES_REGISTRY,
) -> List[RepositoryGovernanceProfile]:
    registry_path = Path(path)
    if not registry_path.exists():
        return []
    with registry_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    repositories = payload.get("repositories") if isinstance(payload, dict) else []
    if not isinstance(repositories, list):
        return []
    profiles: List[RepositoryGovernanceProfile] = []
    for record in repositories:
        if not isinstance(record, dict):
            continue
        if not str(record.get("name") or "").strip():
            continue
        profiles.append(profile_from_repository_registry_record(record))
    return profiles


def _normalize_status(value: str) -> str:
    lowered = value.lower()
    if "disabled" in lowered:
        return "disabled"
    if "archived" in lowered:
        return "archived"
    if "pending" in lowered:
        return "pending"
    if "ready" in lowered or "active" in lowered:
        return "active"
    return "unknown"


def _infer_risk_tier(indicators: List[str]) -> str:
    lowered = " ".join(indicators).lower()
    if any(term in lowered for term in ("secret", "token", "jwt", "hardcoded", "credential")):
        return "high"
    if any(term in lowered for term in ("drift", "missing", "fail", "risk", "unbuildable")):
        return "medium"
    return "low"


def _infer_required_checks(indicators: List[str]) -> List[str]:
    checks = ["git_status"]
    lowered = " ".join(indicators).lower()
    if "eslint" in lowered or "lint" in lowered:
        checks.append("lint")
    if "typescript" in lowered or "tsconfig" in lowered:
        checks.append("typecheck")
    if "build" in lowered or "vite" in lowered or "next.js" in lowered or "pnpm" in lowered:
        checks.append("build")
    if "test" in lowered or "schema" in lowered:
        checks.append("test")
    out: List[str] = []
    for check in checks:
        if check not in out:
            out.append(check)
    return out


def _mentions_secret(value: str) -> bool:
    lowered = value.lower()
    return any(term in lowered for term in ("secret", "token", "jwt", "credential"))


def _optional_str(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _str_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str)]
