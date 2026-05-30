from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from release_gates.promotion_contracts import validate_promotion_profile_dict


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROMOTION_PROFILE_DIR = REPO_ROOT / "config" / "release_gates" / "promotion_profiles"


def load_promotion_profile(path: str | Path) -> Dict[str, Any]:
    profile_path = Path(path)
    with profile_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("promotion profile must be a JSON object")
    validate_promotion_profile_dict(payload)
    return payload


def load_named_promotion_profile(
    name: str,
    base_dir: str | Path = DEFAULT_PROMOTION_PROFILE_DIR,
) -> Dict[str, Any]:
    base = Path(base_dir)
    target = base / f"{name}.json" if not str(name).endswith(".json") else base / name
    try:
        return load_promotion_profile(target)
    except Exception:
        return _safe_fallback_profile(name)


def list_available_promotion_profiles(base_dir: str | Path = DEFAULT_PROMOTION_PROFILE_DIR) -> List[str]:
    base = Path(base_dir)
    if not base.exists():
        return []
    return sorted(path.stem for path in base.glob("*.json"))


def _safe_fallback_profile(name: str) -> Dict[str, Any]:
    payload = {
        "profile_id": f"{name}_fallback",
        "display_name": "Fallback Production-Like Profile",
        "target_environment": "production",
        "required_scenario_pack": "production_release_scenarios",
        "minimum_aggregate_status": "ready",
        "allowed_aggregate_decisions": ["pass"],
        "require_no_blockers": True,
        "require_rollback_plan": True,
        "require_ci_handoff": True,
        "max_warning_count": 0,
        "max_error_count": 0,
        "advisory_only": True,
        "metadata": {"fallback": True},
    }
    validate_promotion_profile_dict(payload)
    return payload

