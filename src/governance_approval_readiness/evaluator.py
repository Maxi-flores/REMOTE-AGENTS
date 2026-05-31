from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from governance_approval_readiness.contracts import (
    GovernanceApprovalReadinessRecord,
    GovernanceApprovalReadinessReport,
    new_id,
    utc_now,
    validate_governance_approval_readiness_report_dict,
)


FORBIDDEN_ARTIFACT_HINTS = {
    "src/orchestrator/platform_engine.py",
    "src/orchastrator/platform_engine.py",
    ".platform_queue",
}


def load_json(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def generate_governance_approval_readiness_report(
    *,
    dossier_report: Dict[str, Any] | None = None,
    dossier_report_path: str | Path | None = None,
    base_dir: str | Path = ".",
) -> Dict[str, Any]:
    root = Path(base_dir)
    if dossier_report is None:
        path = Path(dossier_report_path) if dossier_report_path else (root / ".control_plane" / "governance_recovery_dossiers" / "latest.json")
        dossier_report = load_json(path)

    dossiers = dossier_report.get("dossiers") if isinstance(dossier_report.get("dossiers"), list) else []
    records: List[Dict[str, Any]] = []
    for dossier in dossiers:
        if not isinstance(dossier, dict):
            continue
        records.append(_evaluate_dossier(dossier))

    summary = _build_summary(records)
    report = GovernanceApprovalReadinessReport(
        report_id=new_id("governance_approval_readiness_report"),
        generated_utc=utc_now(),
        source_dossier_report_id=str(dossier_report.get("report_id") or "missing_dossier_report"),
        records=records,
        summary=summary,
        advisory_only=True,
        metadata={
            "advisory_only": True,
            "runtime_unchanged": True,
            "queue_mutation": False,
            "source_dossier_report_path": str(dossier_report_path or root / ".control_plane" / "governance_recovery_dossiers" / "latest.json"),
        },
    ).to_dict()
    validate_governance_approval_readiness_report_dict(report)
    return report


def _evaluate_dossier(dossier: Dict[str, Any]) -> Dict[str, Any]:
    missing: List[str] = []
    title = str(dossier.get("title") or "Unknown dossier")
    advisory_only = bool(dossier.get("advisory_only") is True)
    if not advisory_only:
        missing.append("advisory_only_true")

    target_artifacts = dossier.get("target_artifacts")
    if not isinstance(target_artifacts, list):
        target_artifacts = []
    forbidden_hits = _forbidden_hits(target_artifacts)
    if forbidden_hits:
        missing.append("forbidden_runtime_path_violation")

    validation_commands = dossier.get("validation_commands")
    if not isinstance(validation_commands, list) or not validation_commands:
        missing.append("validation_commands_required")

    rollback = dossier.get("rollback_guidance")
    if not isinstance(rollback, list) or not rollback:
        missing.append("rollback_guidance_required")

    checklist = dossier.get("review_checklist")
    if not isinstance(checklist, list) or not checklist:
        missing.append("review_checklist_required")

    codex_prompt = dossier.get("codex_prompt")
    if not isinstance(codex_prompt, str) or not codex_prompt.strip():
        missing.append("codex_prompt_required")

    risk_level = str(dossier.get("execution_risk") or "unknown").lower()
    if _is_rejected_advisory(dossier):
        status = "rejected_advisory"
    elif _is_blocked(missing):
        status = "blocked"
    elif risk_level in {"high", "critical"} or _needs_review_due_to_scope(dossier):
        status = "needs_review"
    elif advisory_only and risk_level in {"low", "medium"} and not missing:
        status = "ready_for_review"
    else:
        status = "unknown"

    score = _readiness_score(status=status, risk_level=risk_level, missing_count=len(missing))
    recommendation = _recommendation_for_status(status, missing, forbidden_hits, risk_level)
    required_review = status in {"needs_review", "blocked", "rejected_advisory"} or risk_level in {"high", "critical"}

    return GovernanceApprovalReadinessRecord(
        record_id=new_id("governance_approval_readiness"),
        dossier_id=str(dossier.get("dossier_id") or ""),
        title=title,
        approval_status=status,
        readiness_score=score,
        risk_level=risk_level if risk_level else "unknown",
        missing_requirements=missing,
        approval_recommendation=recommendation,
        required_human_review=required_review,
        advisory_only=True,
        metadata={"forbidden_hits": forbidden_hits},
    ).to_dict()


def _forbidden_hits(target_artifacts: List[str]) -> List[str]:
    hits: List[str] = []
    for artifact in target_artifacts:
        if not isinstance(artifact, str):
            continue
        normalized = artifact.replace("\\", "/").lower()
        for forbidden in FORBIDDEN_ARTIFACT_HINTS:
            if forbidden in normalized:
                hits.append(artifact)
                break
    return hits


def _is_blocked(missing: List[str]) -> bool:
    blocking = {"advisory_only_true", "forbidden_runtime_path_violation", "validation_commands_required"}
    return any(item in blocking for item in missing)


def _is_rejected_advisory(dossier: Dict[str, Any]) -> bool:
    text = " ".join(
        str(dossier.get(k) or "")
        for k in ("title", "objective", "codex_prompt")
    ).lower()
    disallowed = ["auto-approve", "automatic approval", "enforcement", "execute automatically", "external repo mutation"]
    return any(token in text for token in disallowed)


def _needs_review_due_to_scope(dossier: Dict[str, Any]) -> bool:
    target_artifacts = dossier.get("target_artifacts")
    if isinstance(target_artifacts, list) and len(target_artifacts) > 6:
        return True
    commands = dossier.get("recommended_commands")
    if isinstance(commands, list):
        broad_markers = ["python -m unittest", "pytest", "npm run"]
        for cmd in commands:
            if isinstance(cmd, str) and any(marker in cmd for marker in broad_markers):
                return True
    return False


def _readiness_score(*, status: str, risk_level: str, missing_count: int) -> int:
    base = {
        "ready_for_review": 90,
        "needs_review": 65,
        "blocked": 25,
        "rejected_advisory": 10,
        "unknown": 40,
    }.get(status, 40)
    if risk_level == "critical":
        base -= 20
    elif risk_level == "high":
        base -= 10
    base -= min(20, missing_count * 5)
    return max(0, min(100, base))


def _recommendation_for_status(status: str, missing: List[str], forbidden_hits: List[str], risk_level: str) -> str:
    if status == "ready_for_review":
        return "Proceed to human approval review with standard checklist verification."
    if status == "needs_review":
        if risk_level in {"high", "critical"}:
            return "Requires elevated human review due to execution risk before approval."
        return "Requires targeted review to close checklist/scope gaps before approval."
    if status == "blocked":
        if forbidden_hits:
            return "Blocked: remove forbidden runtime/queue paths from target artifacts."
        if "validation_commands_required" in missing:
            return "Blocked: add explicit validation commands."
        return "Blocked: resolve mandatory advisory safety requirements."
    if status == "rejected_advisory":
        return "Rejected in advisory mode: remove enforcement/auto-execution language and re-generate dossier."
    return "Insufficient data; review dossier fields and regenerate advisory readiness report."


def _build_summary(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    summary = {
        "ready_for_review": 0,
        "needs_review": 0,
        "blocked": 0,
        "rejected_advisory": 0,
        "unknown": 0,
        "high_risk_count": 0,
        "critical_risk_count": 0,
        "total_records": len(records),
    }
    for record in records:
        if not isinstance(record, dict):
            continue
        status = str(record.get("approval_status") or "unknown")
        summary[status] = int(summary.get(status, 0)) + 1
        risk = str(record.get("risk_level") or "unknown")
        if risk == "high":
            summary["high_risk_count"] += 1
        if risk == "critical":
            summary["critical_risk_count"] += 1
    return summary

