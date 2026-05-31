from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from governance_recovery.contracts import (
    GovernanceRecoveryAction,
    GovernanceRecoveryPlanReport,
    new_id,
    utc_now,
    validate_governance_recovery_plan_report_dict,
)
from governance_recovery.planner import group_actions_into_waves


def load_json(path: str | Path) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        payload = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def generate_governance_recovery_plan_report(*, base_dir: str | Path = ".") -> Dict[str, Any]:
    root = Path(base_dir)
    governance = load_json(root / ".control_plane" / "portfolio_governance_index" / "latest.json")
    score = int(governance.get("governance_score") or 0)
    components = governance.get("components") if isinstance(governance.get("components"), list) else []
    actions = _actions_from_components(components)
    waves = group_actions_into_waves(actions)
    target = min(100, score + sum(int(w.get("expected_score_impact") or 0) for w in waves))
    recommended_sequence = [str(a.get("action_id")) for a in actions if isinstance(a, dict)]
    report = GovernanceRecoveryPlanReport(
        report_id=new_id("governance_recovery_report"),
        generated_utc=utc_now(),
        source_governance_report_id=str(governance.get("report_id") or "missing_governance_report"),
        current_governance_score=score,
        target_governance_score=target,
        actions=actions,
        waves=waves,
        recommended_sequence=recommended_sequence,
        advisory_only=True,
        metadata={
            "advisory_only": True,
            "runtime_unchanged": True,
            "queue_mutation": False,
            "source_artifacts": {"governance_index": str(root / ".control_plane" / "portfolio_governance_index" / "latest.json")},
        },
    ).to_dict()
    validate_governance_recovery_plan_report_dict(report)
    return report


def _actions_from_components(components: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for component in components:
        if not isinstance(component, dict):
            continue
        name = str(component.get("name") or "")
        score = int(component.get("score") or 0)
        cid = str(component.get("component_id") or new_id("component_ref"))
        if name == "Portfolio Readiness" and score < 50:
            out.extend(
                [
                    _action(cid, "Validate and close missing onboarding/readiness repositories", "Improve portfolio readiness by resolving missing onboarding and readiness baselines.", "P1", 15, name, ["python src/portfolio_bootstrap/cli.py --export --export-jsonl", "python src/portfolio_orchestration/cli.py --export --export-jsonl"], ["readiness_recovery", "onboarding_validation"]),
                    _action(cid, "Generate repository intelligence baselines for low-readiness repos", "Increase readiness confidence by generating missing repository intelligence baselines.", "P1", 10, name, ["python src/repository_intelligence/cli.py --export --export-jsonl"], ["repository_intelligence_coverage"]),
                ]
            )
        if name == "Onboarding Coverage" and score < 50:
            out.extend(
                [
                    _action(cid, "Resolve P1 onboarding recommendations", "Address highest-priority onboarding recommendations first.", "P1", 12, name, ["python src/portfolio_onboarding_recommendations/cli.py --export --export-jsonl"], ["onboarding_priority_reduction"]),
                    _action(cid, "Re-run bootstrap and onboarding recommendation refresh", "Refresh onboarding artifacts to ensure recommendations match latest repository state.", "P2", 5, name, ["python src/portfolio_bootstrap/cli.py --export --export-jsonl", "python src/portfolio_onboarding_recommendations/cli.py --export --export-jsonl"], ["artifact_refresh"]),
                ]
            )
        if name == "Dependency Risk" and score < 70:
            out.extend(
                [
                    _action(cid, "Reduce high/critical dependency findings", "Resolve top dependency blockers and unknown references.", "P2", 12, name, ["python src/portfolio_dependencies/cli.py --export --export-jsonl", "python src/portfolio_critical_path/cli.py --export --export-jsonl"], ["dependency_risk_reduction"]),
                ]
            )
        if name == "Drift Health" and score < 70:
            out.extend(
                [
                    _action(cid, "Resolve missing dependency references and stale artifacts", "Clean cross-artifact drift and stale report chains.", "P2", 8, name, ["python src/portfolio_drift/cli.py --export --export-jsonl", "python src/portfolio_roadmap/cli.py --export --export-jsonl", "python src/portfolio_progress/cli.py --export --export-jsonl"], ["drift_reconciliation"]),
                ]
            )
        if name == "Roadmap Completeness" and score < 70:
            out.append(
                _action(
                    cid,
                    "Regenerate strategic roadmap from latest critical path",
                    "Improve roadmap completeness by regenerating from up-to-date critical path analysis.",
                    "P2",
                    7,
                    name,
                    ["python src/portfolio_critical_path/cli.py --export --export-jsonl", "python src/portfolio_roadmap/cli.py --export --export-jsonl"],
                    ["roadmap_wave_coverage"],
                )
            )
        if name == "Progress Trend" and score < 70:
            out.append(
                _action(
                    cid,
                    "Build additional progress history snapshots",
                    "Generate consecutive snapshots to stabilize trend confidence.",
                    "P3",
                    4,
                    name,
                    ["python src/portfolio_progress/cli.py --export --export-jsonl"],
                    ["trend_confidence"],
                )
            )
        if name == "Critical Path Risk" and score < 70:
            out.append(
                _action(
                    cid,
                    "Execute near-term critical-path actions manually",
                    "Prioritize near-term critical-path recommendations during manual planning cycles.",
                    "P2",
                    8,
                    name,
                    ["python src/portfolio_critical_path/cli.py --print", "python src/portfolio_roadmap/cli.py --print"],
                    ["critical_path_priority_alignment"],
                )
            )
    # deterministic dedupe by title
    dedup: Dict[str, Dict[str, Any]] = {}
    for action in out:
        if isinstance(action, dict):
            dedup[str(action.get("title") or action.get("action_id"))] = action
    ordered = sorted(dedup.values(), key=lambda a: (_priority_order(str(a.get("priority") or "P4")), -int(a.get("expected_score_impact") or 0), str(a.get("title") or "")))
    return ordered


def _action(
    source_component_id: str,
    title: str,
    description: str,
    priority: str,
    impact: int,
    target_component: str,
    commands: List[str],
    focus: List[str],
) -> Dict[str, Any]:
    return GovernanceRecoveryAction(
        action_id=new_id("governance_recovery_action"),
        source_component_id=source_component_id,
        title=title,
        description=description,
        priority=priority,
        expected_score_impact=impact,
        target_component=target_component,
        recommended_commands=commands,
        validation_focus=focus,
        advisory_only=True,
        metadata={"impact_estimate_advisory": True},
    ).to_dict()


def _priority_order(priority: str) -> int:
    return {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}.get(priority, 4)

