from __future__ import annotations

from typing import Any, Dict, List, Tuple


def infer_subsystem(path: str) -> str:
    normalized = str(path).replace("\\", "/").lower()
    if normalized.endswith("test_mission_engine_cli.py") or normalized.endswith("test_mission_engine.py"):
        return "mission_engine"
    if normalized.endswith("test_orchestrator.py"):
        return "orchestrator"
    if normalized.endswith("test_orchastrator.py"):
        return "orchastrator"
    if normalized.endswith("test_routers.py"):
        return "routers"
    if normalized.endswith("test_tools.py"):
        return "tools"
    if normalized.endswith("test_ui.py"):
        return "ui"
    if "/strategic_missions/" in normalized or normalized.endswith("strategic-mission-generation.md"):
        return "strategic_missions"
    if "/mission_engine/" in normalized:
        return "mission_engine"
    if "/orchestrator/" in normalized:
        return "orchestrator"
    if "/orchastrator/" in normalized:
        return "orchastrator"
    if "/router" in normalized or "/routers/" in normalized:
        return "routers"
    if "/tools/" in normalized:
        return "tools"
    if "/ui/" in normalized:
        return "ui"
    if normalized.startswith("docs/"):
        return "docs"
    return "system"


def infer_change_type(path: str) -> str:
    normalized = str(path).replace("\\", "/").lower()
    name = normalized.split("/")[-1]
    if name.endswith("_cli.py"):
        return "add_cli_test"
    if name.startswith("test_") and name.endswith("_contracts.py"):
        return "add_contract_test"
    if "runtime_compat" in name or "compat" in name:
        return "add_runtime_compat_test"
    if name.startswith("test_") and name.endswith(".py"):
        return "add_test"
    if normalized.startswith("docs/") and normalized.endswith(".md"):
        return "add_docs"
    return "add_update"


def detect_broad_package(package: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    files = _as_list(package.get("target_files"))
    subsystems = {infer_subsystem(path) for path in files}
    change_types = {infer_change_type(path) for path in files}
    commands = _as_list(package.get("validation_commands"))
    reasons: List[str] = []
    if len(files) > 3:
        reasons.append("target_files_gt_3")
    if len(subsystems) > 1:
        reasons.append("multi_subsystem")
    if len(commands) > 2:
        reasons.append("validation_commands_gt_2")
    if len(change_types) > 1:
        reasons.append("mixed_change_types")
    return (len(reasons) > 0, {"reasons": reasons, "subsystems": sorted(subsystems), "change_types": sorted(change_types)})


def split_groups(package: Dict[str, Any]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    files = _as_list(package.get("target_files"))
    group_map: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for file_path in files:
        subsystem = infer_subsystem(file_path)
        change_type = infer_change_type(file_path)
        key = (subsystem, change_type)
        if key not in group_map:
            group_map[key] = {"target_files": [], "validation_commands": []}
        group_map[key]["target_files"].append(file_path)
    commands = _as_list(package.get("validation_commands"))
    for command in commands:
        command_lower = command.lower()
        assigned = False
        for key, data in group_map.items():
            subsystem, change_type = key
            if subsystem in command_lower or _command_matches_change_type(command_lower, change_type):
                data["validation_commands"].append(command)
                assigned = True
        if not assigned and group_map:
            first_key = sorted(group_map.keys())[0]
            group_map[first_key]["validation_commands"].append(command)
    for data in group_map.values():
        data["target_files"] = _dedupe(data["target_files"])
        data["validation_commands"] = _dedupe(data["validation_commands"])
    return group_map


def _command_matches_change_type(command_lower: str, change_type: str) -> bool:
    if change_type == "add_cli_test":
        return "cli" in command_lower
    if change_type == "add_contract_test":
        return "contract" in command_lower
    if change_type == "add_runtime_compat_test":
        return "compat" in command_lower
    if change_type == "add_test":
        return "test" in command_lower
    if change_type == "add_docs":
        return "repository_intelligence_analyzer" in command_lower
    return False


def _as_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    out: List[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            out.append(text)
    return out


def _dedupe(items: List[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for item in items:
        text = str(item).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out
