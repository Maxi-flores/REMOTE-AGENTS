from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from release_gates.contracts import validate_gate_policy_dict


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY_DIR = REPO_ROOT / "config" / "release_gates"


def load_gate_policy(path: str | Path) -> Dict[str, Any]:
    policy_path = Path(path)
    with policy_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        raise ValueError("policy must be a JSON object")
    validate_gate_policy_dict(payload)
    return payload


def load_named_gate_policy(name: str, base_dir: str | Path = DEFAULT_POLICY_DIR) -> Dict[str, Any]:
    base = Path(base_dir)
    target = base / f"{name}.json" if not str(name).endswith(".json") else base / name
    try:
        return load_gate_policy(target)
    except Exception:
        return _safe_strict_fallback(name)


def list_available_gate_policies(base_dir: str | Path = DEFAULT_POLICY_DIR) -> List[str]:
    base = Path(base_dir)
    if not base.exists():
        return []
    return sorted(path.stem for path in base.glob("*.json"))


def _safe_strict_fallback(name: str) -> Dict[str, Any]:
    policy = {
        "policy_id": f"{name}_fallback",
        "display_name": "Fallback Strict Advisory Gate",
        "minimum_readiness_score": 95,
        "block_on_critical_findings": True,
        "block_on_malformed_artifacts": True,
        "block_on_missing_artifacts": True,
        "block_on_unsupported_versions": True,
        "max_warning_count": 0,
        "max_error_count": 0,
        "required_artifacts": [
            "control_plane_snapshot",
            "sentient_ui_view_model",
        ],
        "advisory_only": True,
        "metadata": {"fallback": True},
    }
    validate_gate_policy_dict(policy)
    return policy

