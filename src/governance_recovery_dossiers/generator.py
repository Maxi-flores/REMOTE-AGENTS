from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from governance_recovery_dossiers.checklists import build_review_checklist, build_rollback_guidance
from governance_recovery_dossiers.contracts import (
    GovernanceRecoveryDossier,
    GovernanceRecoveryDossierReport,
    new_id,
    utc_now,
    validate_governance_recovery_dossier_report_dict,
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


def generate_governance_recovery_dossier_report(
    *,
    recovery_report: Dict[str, Any] | None = None,
    recovery_report_path: str | Path | None = None,
    base_dir: str | Path = ".",
) -> Dict[str, Any]:
    root = Path(base_dir)
    if recovery_report is None:
        path = Path(recovery_report_path) if recovery_report_path else (root / ".control_plane" / "governance_recovery" / "latest.json")
        recovery_report = load_json(path)

    actions = recovery_report.get("actions") if isinstance(recovery_report.get("actions"), list) else []
    waves = recovery_report.get("waves") if isinstance(recovery_report.get("waves"), list) else []
    wave_by_action = _wave_lookup(waves)

    dossiers: List[Dict[str, Any]] = []
    for action in actions:
        if not isinstance(action, dict):
            continue
        source_wave_id = wave_by_action.get(str(action.get("action_id") or ""), "wave_unknown")
        target_artifacts = _target_artifacts_for_action(action)
        validation_commands = _validation_commands_for_action(action)
        checklist = build_review_checklist(action=action, target_artifacts=target_artifacts)
        rollback = build_rollback_guidance(target_artifacts=target_artifacts)
        codex_prompt = _codex_prompt(action, target_artifacts, validation_commands)
        dossier = GovernanceRecoveryDossier(
            dossier_id=new_id("governance_recovery_dossier"),
            source_action_id=str(action.get("action_id") or ""),
            source_wave_id=source_wave_id,
            title=f"Dossier: {str(action.get('title') or 'Governance recovery action')}",
            objective=str(action.get("description") or "Execute governance recovery action through human-reviewed manual steps."),
            target_component=str(action.get("target_component") or "Governance"),
            target_artifacts=target_artifacts,
            recommended_commands=[str(c) for c in action.get("recommended_commands", []) if isinstance(c, str)],
            validation_commands=validation_commands,
            review_checklist=checklist,
            rollback_guidance=rollback,
            codex_prompt=codex_prompt,
            execution_risk=_execution_risk_from_priority(str(action.get("priority") or "P3")),
            advisory_only=True,
            metadata={
                "advisory_only": True,
                "priority": str(action.get("priority") or "P3"),
                "expected_score_impact": int(action.get("expected_score_impact") or 0),
            },
        ).to_dict()
        dossiers.append(dossier)

    report = GovernanceRecoveryDossierReport(
        report_id=new_id("governance_recovery_dossier_report"),
        generated_utc=utc_now(),
        source_recovery_report_id=str(recovery_report.get("report_id") or "missing_governance_recovery_report"),
        dossiers=dossiers,
        wave_summary=_wave_summary(dossiers, waves),
        advisory_only=True,
        metadata={
            "advisory_only": True,
            "runtime_unchanged": True,
            "queue_mutation": False,
            "source_recovery_report_path": str(recovery_report_path or root / ".control_plane" / "governance_recovery" / "latest.json"),
        },
    ).to_dict()
    validate_governance_recovery_dossier_report_dict(report)
    return report


def _wave_lookup(waves: List[Dict[str, Any]]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for wave in waves:
        if not isinstance(wave, dict):
            continue
        wave_id = str(wave.get("wave_id") or "wave_unknown")
        action_ids = wave.get("actions")
        if not isinstance(action_ids, list):
            continue
        for action_id in action_ids:
            if isinstance(action_id, str):
                out[action_id] = wave_id
    return out


def _wave_summary(dossiers: List[Dict[str, Any]], waves: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    summary_by_wave: Dict[str, Dict[str, Any]] = {}
    for dossier in dossiers:
        if not isinstance(dossier, dict):
            continue
        wave_id = str(dossier.get("source_wave_id") or "wave_unknown")
        current = summary_by_wave.setdefault(
            wave_id,
            {
                "wave_id": wave_id,
                "dossier_count": 0,
                "high_risk_count": 0,
                "critical_risk_count": 0,
                "action_ids": [],
            },
        )
        current["dossier_count"] += 1
        risk = str(dossier.get("execution_risk") or "low")
        if risk == "high":
            current["high_risk_count"] += 1
        if risk == "critical":
            current["critical_risk_count"] += 1
        current["action_ids"].append(str(dossier.get("source_action_id") or ""))

    wave_titles = {str(w.get("wave_id") or ""): str(w.get("title") or "") for w in waves if isinstance(w, dict)}
    out: List[Dict[str, Any]] = []
    for wave_id, info in summary_by_wave.items():
        info["wave_title"] = wave_titles.get(wave_id, wave_id)
        out.append(info)
    return sorted(out, key=lambda item: str(item.get("wave_id") or ""))


def _target_artifacts_for_action(action: Dict[str, Any]) -> List[str]:
    text = f"{str(action.get('title') or '')} {str(action.get('description') or '')}".lower()
    artifacts: List[str] = []
    if "onboarding" in text or "readiness" in text:
        artifacts.extend(
            [
                ".config/portfolio/portfolio_registry.json",
                ".control_plane/portfolio_bootstrap/latest.json",
                ".control_plane/portfolio_onboarding_recommendations/latest.json",
                ".control_plane/portfolio/latest.json",
            ]
        )
    if "dependency" in text or "critical path" in text:
        artifacts.extend(
            [
                ".config/portfolio/dependencies.json",
                ".control_plane/portfolio_dependencies/latest.json",
                ".control_plane/portfolio_critical_path/latest.json",
            ]
        )
    if "drift" in text or "stale" in text:
        artifacts.extend(
            [
                ".control_plane/portfolio_drift/latest.json",
                ".control_plane/portfolio_roadmap/latest.json",
                ".control_plane/portfolio_progress/latest.json",
            ]
        )
    if "roadmap" in text or "progress" in text:
        artifacts.extend(
            [
                ".control_plane/portfolio_roadmap/latest.json",
                ".control_plane/portfolio_progress/latest.json",
                ".control_plane/portfolio_governance_index/latest.json",
            ]
        )
    if not artifacts:
        artifacts = [".control_plane/portfolio_governance_index/latest.json"]
    dedup: List[str] = []
    seen = set()
    for artifact in artifacts:
        if artifact not in seen:
            seen.add(artifact)
            dedup.append(artifact)
    return dedup


def _validation_commands_for_action(action: Dict[str, Any]) -> List[str]:
    title = f"{str(action.get('title') or '').lower()} {str(action.get('description') or '').lower()}"
    commands = [
        "python src/portfolio_orchestration/cli.py --print",
        "python src/portfolio_governance_index/cli.py --print",
    ]
    if "onboarding" in title or "readiness" in title:
        commands.insert(0, "python src/portfolio_onboarding_recommendations/cli.py --print")
    if "dependency" in title or "critical path" in title:
        commands.insert(0, "python src/portfolio_dependencies/cli.py --print")
    if "drift" in title or "stale" in title:
        commands.insert(0, "python src/portfolio_drift/cli.py --print")
    return commands


def _execution_risk_from_priority(priority: str) -> str:
    if priority == "P0":
        return "critical"
    if priority == "P1":
        return "high"
    if priority == "P2":
        return "medium"
    return "low"


def _codex_prompt(action: Dict[str, Any], target_artifacts: List[str], validation_commands: List[str]) -> str:
    recommended = [str(c) for c in action.get("recommended_commands", []) if isinstance(c, str)]
    lines = [
        "You are implementing a Governance Recovery Execution Dossier in advisory-only mode.",
        "Strict constraints:",
        "- Do not modify platform_engine.py.",
        "- Do not modify .platform_queue/next_task.json or queue semantics.",
        "- Do not execute commands automatically without explicit human review and manual trigger.",
        "- Do not modify external repositories.",
        "- Use only allowed artifact paths listed below.",
        "",
        f"Target component: {str(action.get('target_component') or 'Governance')}",
        f"Objective: {str(action.get('description') or '')}",
        "",
        "Allowed artifact paths:",
    ]
    lines.extend([f"- {artifact}" for artifact in target_artifacts] or ["- .control_plane/"])
    lines.extend(
        [
            "",
            "Forbidden paths:",
            "- src/orchestrator/platform_engine.py",
            "- src/orchastrator/platform_engine.py",
            "- .platform_queue/next_task.json",
            "",
            "Recommended manual commands:",
        ]
    )
    lines.extend([f"- {cmd}" for cmd in recommended] or ["- (none provided)"])
    lines.extend(["", "Validation commands:"])
    lines.extend([f"- {cmd}" for cmd in validation_commands])
    lines.extend(
        [
            "",
            "Expected outputs:",
            "- Updated advisory artifacts for the target component.",
            "- No runtime behavior change.",
            "- Queue contract untouched.",
        ]
    )
    return "\n".join(lines).strip() + "\n"

