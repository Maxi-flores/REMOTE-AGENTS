from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from remediation_handoff.contracts import (
    ImplementationPackage,
    ImplementationPackageReport,
    new_id,
    utc_now,
    validate_implementation_package_report_dict,
)
from remediation_handoff.prompt_builder import build_codex_prompt_for_package


def load_remediation_report(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def generate_implementation_package_report(
    *,
    remediation_report: Dict[str, Any] | None = None,
    remediation_report_path: str | Path | None = None,
    base_dir: str | Path = ".",
    limit: int | None = None,
) -> Dict[str, Any]:
    root = Path(base_dir)
    source_path = Path(remediation_report_path) if remediation_report_path else None
    if remediation_report is None:
        if source_path is None:
            latest = root / ".control_plane" / "remediation_plans" / "latest.json"
            source_path = latest if latest.exists() else (root / ".control_plane" / "remediation_plans" / "remediation_plan_report.json")
        remediation_report = load_remediation_report(source_path)

    batches = remediation_report.get("batches", []) if isinstance(remediation_report, dict) else []
    items = remediation_report.get("items", []) if isinstance(remediation_report, dict) else []
    packages = _packages_from_batches(batches, items)
    if isinstance(limit, int) and limit > 0:
        packages = packages[:limit]

    report = ImplementationPackageReport(
        report_id=new_id("remediation_handoff_report"),
        generated_utc=utc_now(),
        source_remediation_report_id=str(remediation_report.get("report_id") or "remediation_report_missing"),
        packages=packages,
        advisory_only=True,
        metadata={
            "advisory_only": True,
            "source_report_path": str(source_path) if source_path else None,
            "base_dir": str(root),
            "auto_execution": False,
        },
    ).to_dict()
    validate_implementation_package_report_dict(report)
    return report


def _packages_from_batches(batches: Any, items: Any) -> List[Dict[str, Any]]:
    if not isinstance(batches, list):
        return []
    item_index = _item_index(items)
    out: List[Dict[str, Any]] = []
    for batch in batches:
        if not isinstance(batch, dict):
            continue
        package = _package_from_batch(batch, item_index)
        package["codex_prompt"] = build_codex_prompt_for_package(package)
        out.append(package)
    return out


def _item_index(items: Any) -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    if not isinstance(items, list):
        return index
    for item in items:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("item_id") or "")
        if item_id:
            index[item_id] = item
    return index


def _package_from_batch(batch: Dict[str, Any], item_index: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    item_ids = [str(x) for x in batch.get("item_ids", []) if isinstance(x, str)]
    linked_items = [item_index[item_id] for item_id in item_ids if item_id in item_index]
    title = _title_from_batch(batch, linked_items)
    target_files = _target_files_for_items(linked_items)
    expected_changes = _expected_changes_for_items(linked_items, target_files)
    validation_commands = _validation_commands_for_items(linked_items)
    risks = _risks_for_batch(batch, linked_items)
    objective = _objective_from_batch(batch, linked_items)
    human_review_notes = _human_review_notes(batch, linked_items)

    package = ImplementationPackage(
        package_id=new_id("implementation_package"),
        generated_utc=utc_now(),
        source_batch_id=str(batch.get("batch_id") or "unknown_batch"),
        title=title,
        objective=objective,
        target_files=target_files,
        expected_changes=expected_changes,
        validation_commands=validation_commands,
        risks=risks,
        advisory_only=True,
        metadata={
            "repository": str(batch.get("repository") or "unknown"),
            "priority": str(batch.get("priority") or "P4"),
            "human_review_notes": human_review_notes,
            "advisory_only": True,
        },
    )
    return package.to_dict()


def _title_from_batch(batch: Dict[str, Any], linked_items: List[Dict[str, Any]]) -> str:
    if linked_items:
        first_title = str(linked_items[0].get("title") or "").strip()
        if first_title:
            return f"Implement remediation batch: {first_title}"
    return str(batch.get("name") or "Implementation Package")


def _objective_from_batch(batch: Dict[str, Any], linked_items: List[Dict[str, Any]]) -> str:
    if linked_items:
        return f"Address {len(linked_items)} remediation item(s) from batch '{str(batch.get('name') or '')}'."
    return f"Convert remediation batch '{str(batch.get('name') or '')}' into an actionable implementation plan."


def _target_files_for_items(linked_items: List[Dict[str, Any]]) -> List[str]:
    files: List[str] = []
    for item in linked_items:
        title = str(item.get("title") or "").lower()
        category = str(item.get("category") or "").lower()
        if "cli without matching cli test" in title:
            module = title.split(":")[-1].strip().replace("-", "_")
            files.append(f"tests/test_{module}_cli.py")
        elif "source module without direct tests" in title:
            module = title.split(":")[-1].strip().replace("-", "_")
            files.append(f"tests/test_{module}.py")
        elif "without subsystem docs" in title:
            module = title.split(":")[-1].strip().replace("_", "-")
            files.append(f"docs/{module}.md")
        elif category == "tests":
            files.append("tests/")
        elif category == "docs":
            files.append("docs/")
        elif category == "config":
            files.append("config/")
        else:
            files.append("src/")
    return _dedupe(files)


def _expected_changes_for_items(linked_items: List[Dict[str, Any]], target_files: List[str]) -> Dict[str, Any]:
    additions: List[str] = []
    updates: List[str] = []
    notes: List[str] = []
    for file_path in target_files:
        if file_path.endswith(".py") or file_path.endswith(".md"):
            additions.append(file_path)
        else:
            updates.append(file_path)
    for item in linked_items:
        notes.append(str(item.get("suggested_action") or "Review and remediate item."))
    return {
        "file_additions": _dedupe(additions),
        "file_updates": _dedupe(updates),
        "notes": _dedupe(notes),
    }


def _validation_commands_for_items(linked_items: List[Dict[str, Any]]) -> List[str]:
    commands: List[str] = []
    for item in linked_items:
        title = str(item.get("title") or "").lower()
        if "cli without matching cli test" in title:
            module = title.split(":")[-1].strip().replace("-", "_")
            commands.append(f"python -m unittest tests.test_{module}_cli -v")
        elif "source module without direct tests" in title:
            module = title.split(":")[-1].strip().replace("-", "_")
            commands.append(f"python -m unittest tests.test_{module} -v")
        elif "without subsystem docs" in title:
            commands.append("python -m unittest tests.test_repository_intelligence_analyzer -v")
    if not commands:
        commands.append("python -m unittest -v")
    return _dedupe(commands)


def _risks_for_batch(batch: Dict[str, Any], linked_items: List[Dict[str, Any]]) -> List[str]:
    priority = str(batch.get("priority") or "P4")
    if priority in {"P0", "P1"}:
        base = ["Medium: broad change surface across multiple remediation items."]
    elif priority == "P2":
        base = ["Low: documentation or test-coverage dominant remediation."]
    else:
        base = ["Low: maintenance-level remediation package."]
    if len(linked_items) > 5:
        base.append("Medium: package size may require splitting for safer review.")
    return base


def _human_review_notes(batch: Dict[str, Any], linked_items: List[Dict[str, Any]]) -> List[str]:
    notes = [
        "Review target file list before implementation.",
        "Confirm validation commands match repository test naming conventions.",
        "Split package manually if review scope is too wide.",
    ]
    if str(batch.get("priority") or "P4") in {"P0", "P1"}:
        notes.append("Prioritize this package in the next manual implementation cycle.")
    if not linked_items:
        notes.append("Linked item details were unavailable; derive file-level plan manually.")
    return notes


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
