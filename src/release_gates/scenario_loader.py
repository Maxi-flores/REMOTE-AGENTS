from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from release_gates.scenario_contracts import validate_scenario_pack_dict


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCENARIO_DIR = REPO_ROOT / "config" / "release_gates" / "scenario_packs"


def load_scenario_pack(path: str | Path) -> Dict[str, Any]:
    scenario_path = Path(path)
    with scenario_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        raise ValueError("scenario pack must be a JSON object")
    validate_scenario_pack_dict(payload)
    return payload


def load_named_scenario_pack(name: str, base_dir: str | Path = DEFAULT_SCENARIO_DIR) -> Dict[str, Any]:
    base = Path(base_dir)
    target = base / f"{name}.json" if not str(name).endswith(".json") else base / name
    try:
        return load_scenario_pack(target)
    except Exception:
        return _safe_default_pack(name)


def list_available_scenario_packs(base_dir: str | Path = DEFAULT_SCENARIO_DIR) -> List[str]:
    base = Path(base_dir)
    if not base.exists():
        return []
    return sorted(path.stem for path in base.glob("*.json"))


def _safe_default_pack(name: str) -> Dict[str, Any]:
    payload = {
        "scenario_pack_id": f"{name}_fallback",
        "display_name": "Fallback Scenario Pack",
        "policy_names": ["default_gate_policy"],
        "comparison_strategy": "compare_all",
        "advisory_only": True,
        "metadata": {"fallback": True},
    }
    validate_scenario_pack_dict(payload)
    return payload

