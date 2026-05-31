from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from execution_dossier.checklists import build_review_checklist, build_rollback_guidance
from execution_dossier.contracts import (
    ExecutionDossier,
    ExecutionDossierReport,
    ExecutionPacket,
    new_id,
    utc_now,
    validate_execution_dossier_report_dict,
)


def load_json(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def generate_execution_dossier_report(
    *,
    work_queue_report: Dict[str, Any] | None = None,
    work_queue_path: str | Path | None = None,
    base_dir: str | Path = ".",
    limit: int | None = None,
) -> Dict[str, Any]:
    root = Path(base_dir)
    if work_queue_report is None:
        path = Path(work_queue_path) if work_queue_path else (root / ".control_plane" / "work_queue" / "latest.json")
        work_queue_report = load_json(path)
    refined = load_json(root / ".control_plane" / "handoff_refinements" / "latest.json")
    handoff = load_json(root / ".control_plane" / "remediation_handoffs" / "latest.json")
    refined_index = {
        str(pkg.get("refined_package_id")): pkg
        for pkg in (refined.get("refined_packages") if isinstance(refined.get("refined_packages"), list) else [])
        if isinstance(pkg, dict)
    }
    handoff_index = {
        str(pkg.get("source_batch_id")): pkg
        for pkg in (handoff.get("packages") if isinstance(handoff.get("packages"), list) else [])
        if isinstance(pkg, dict)
    }
    queue_items = work_queue_report.get("queue_items") if isinstance(work_queue_report.get("queue_items"), list) else []

    dossiers: List[Dict[str, Any]] = []
    packets: List[Dict[str, Any]] = []
    for item in queue_items:
        if not isinstance(item, dict):
            continue
        src_pkg_id = str(item.get("source_refined_package_id") or "")
        pkg = refined_index.get(src_pkg_id, {})
        source_batch = str((item.get("metadata") or {}).get("source_batch_id") or pkg.get("source_batch_id") or "")
        handoff_pkg = handoff_index.get(source_batch, {})
        dossier = _build_dossier(item, pkg, handoff_pkg)
        packet = _build_packet(dossier)
        dossiers.append(dossier)
        packets.append(packet)

    if isinstance(limit, int) and limit > 0:
        dossiers = dossiers[:limit]
        keep_ids = {d["dossier_id"] for d in dossiers if isinstance(d, dict)}
        packets = [p for p in packets if isinstance(p, dict) and str(p.get("dossier_id")) in keep_ids]

    report = ExecutionDossierReport(
        report_id=new_id("execution_dossier_report"),
        generated_utc=utc_now(),
        dossiers=dossiers,
        execution_packets=packets,
        advisory_only=True,
        metadata={
            "advisory_only": True,
            "source_work_queue_report_id": str(work_queue_report.get("report_id") or "work_queue_report_missing"),
            "queue_mutation": False,
            "runtime_unchanged": True,
        },
    ).to_dict()
    validate_execution_dossier_report_dict(report)
    return report


def _build_dossier(item: Dict[str, Any], refined_pkg: Dict[str, Any], handoff_pkg: Dict[str, Any]) -> Dict[str, Any]:
    target_files = refined_pkg.get("target_files") if isinstance(refined_pkg.get("target_files"), list) else []
    expected_changes = refined_pkg.get("expected_changes") if isinstance(refined_pkg.get("expected_changes"), dict) else {}
    validation_commands = refined_pkg.get("validation_commands") if isinstance(refined_pkg.get("validation_commands"), list) else []
    score = int(item.get("readiness_score") or 0)
    risk = _execution_risk(score, int(item.get("risk_score") or 0))
    base = {
        "target_files": target_files,
    }
    checklist = build_review_checklist(base)
    rollback = build_rollback_guidance(base)
    title = str(refined_pkg.get("title") or item.get("title") or "Execution Dossier")
    objective = str(
        refined_pkg.get("objective")
        or handoff_pkg.get("objective")
        or f"Execute queue item '{title}' with validated scope and rollback guidance."
    )
    dossier = ExecutionDossier(
        dossier_id=new_id("dossier"),
        generated_utc=utc_now(),
        source_queue_item_id=str(item.get("queue_item_id") or ""),
        source_package_id=str(item.get("source_refined_package_id") or ""),
        title=title,
        objective=objective,
        subsystem=str(item.get("subsystem") or refined_pkg.get("subsystem") or "system"),
        target_files=[str(f) for f in target_files if isinstance(f, str)],
        expected_changes=expected_changes,
        validation_commands=[str(c) for c in validation_commands if isinstance(c, str)],
        rollback_guidance=rollback,
        review_checklist=checklist,
        execution_readiness_score=score,
        execution_risk=risk,
        advisory_only=True,
        metadata={
            "advisory_only": True,
            "traceability_refs": list(refined_pkg.get("traceability_refs", [])) if isinstance(refined_pkg.get("traceability_refs"), list) else [],
            "execution_readiness": str(item.get("execution_readiness") or "unknown"),
        },
    ).to_dict()
    return dossier


def _build_packet(dossier: Dict[str, Any]) -> Dict[str, Any]:
    title = str(dossier.get("title") or "Execution Dossier")
    objective = str(dossier.get("objective") or "")
    files = dossier.get("target_files") if isinstance(dossier.get("target_files"), list) else []
    commands = dossier.get("validation_commands") if isinstance(dossier.get("validation_commands"), list) else []
    checklist = dossier.get("review_checklist") if isinstance(dossier.get("review_checklist"), list) else []
    rollback = dossier.get("rollback_guidance") if isinstance(dossier.get("rollback_guidance"), list) else []
    prompt_lines = [
        "You are executing a reviewed advisory execution dossier.",
        "Constraints:",
        "- Do not alter platform_engine.py behavior.",
        "- Do not alter .platform_queue semantics.",
        "- Keep changes limited to target files.",
        "",
        f"Title: {title}",
        f"Objective: {objective}",
        "",
        "Target Files:",
    ]
    prompt_lines.extend([f"- {f}" for f in files] or ["- (none provided)"])
    prompt_lines.append("")
    prompt_lines.append("Validation Commands:")
    prompt_lines.extend([f"- {c}" for c in commands] or ["- python -m unittest -v"])
    prompt_lines.append("")
    prompt_lines.append("Review Checklist:")
    prompt_lines.extend([f"- {c}" for c in checklist] or ["- Review checklist unavailable"])
    prompt_lines.append("")
    prompt_lines.append("Rollback Guidance:")
    prompt_lines.extend([f"- {r}" for r in rollback] or ["- Rollback guidance unavailable"])
    packet = ExecutionPacket(
        packet_id=new_id("execution_packet"),
        dossier_id=str(dossier.get("dossier_id") or ""),
        codex_prompt="\n".join(prompt_lines).strip() + "\n",
        execution_summary=f"Execute dossier '{title}' for subsystem '{str(dossier.get('subsystem') or 'system')}'.",
        validation_summary=f"Run {len(commands)} validation command(s) and confirm checklist completion.",
        advisory_only=True,
        metadata={"advisory_only": True},
    ).to_dict()
    return packet


def _execution_risk(readiness_score: int, risk_score: int) -> str:
    if risk_score >= 85 or readiness_score < 30:
        return "critical"
    if risk_score >= 70 or readiness_score < 50:
        return "high"
    if risk_score >= 45 or readiness_score < 80:
        return "medium"
    return "low"
