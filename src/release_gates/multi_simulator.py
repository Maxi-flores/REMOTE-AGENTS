from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from release_gates.policy_loader import load_named_gate_policy
from release_gates.scenario_loader import load_named_scenario_pack
from release_gates.scenario_contracts import ScenarioComparisonResult, new_id, utc_now
from release_gates.simulator import simulate_gate


def simulate_scenario_pack(report: Dict[str, Any], scenario_pack: Dict[str, Any]) -> Dict[str, Any]:
    policy_names = [str(v) for v in scenario_pack.get("policy_names", []) if isinstance(v, str)]
    decisions: List[Dict[str, Any]] = []
    for name in policy_names:
        policy = load_named_gate_policy(name)
        decision = simulate_gate(report, policy)
        decision_with_policy = dict(decision)
        decision_with_policy["policy_name"] = name
        decisions.append({"policy_name": name, "policy": policy, "decision": decision_with_policy})

    aggregate_decision, blockers, warnings = aggregate_policy_decisions(
        [entry["decision"] for entry in decisions],
        scenario_pack.get("comparison_strategy", "compare_all"),
    )
    aggregate_status = _aggregate_status_from_decision(aggregate_decision)

    result = ScenarioComparisonResult(
        comparison_id=new_id("scenario_comparison"),
        scenario_pack_id=str(scenario_pack.get("scenario_pack_id") or "unknown_scenario"),
        report_id=report.get("report_id") if isinstance(report.get("report_id"), str) else None,
        generated_utc=utc_now(),
        comparison_strategy=scenario_pack.get("comparison_strategy", "compare_all"),  # type: ignore[arg-type]
        policy_decisions=decisions,
        aggregate_decision=aggregate_decision,  # type: ignore[arg-type]
        aggregate_status=aggregate_status,  # type: ignore[arg-type]
        blockers=blockers,
        warnings=warnings,
        summary={
            "policy_count": len(policy_names),
            "decision_counts": _decision_counts([entry["decision"] for entry in decisions]),
        },
        advisory_only=bool(scenario_pack.get("advisory_only", True)),
        metadata={"advisory_only": bool(scenario_pack.get("advisory_only", True))},
    )
    return result.to_dict()


def simulate_scenario_pack_from_report_file(
    report_path: str | Path = ".release_reports/release_readiness.json",
    scenario_pack_name: str = "default_release_scenarios",
) -> Dict[str, Any]:
    path = Path(report_path)
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        report = payload if isinstance(payload, dict) else {}
    else:
        report = {
            "report_id": None,
            "readiness_score": 0,
            "blockers": ["release readiness report missing"],
            "warnings": [],
            "findings": [],
            "checked_artifacts": [],
            "readiness_status": "unknown",
        }
    pack = load_named_scenario_pack(scenario_pack_name)
    return simulate_scenario_pack(report, pack)


def aggregate_policy_decisions(policy_decisions: List[Dict[str, Any]], strategy: str) -> Tuple[str, List[str], List[str]]:
    decisions = [str(item.get("decision") or "unknown") for item in policy_decisions]
    blockers = _dedupe(
        [str(b) for item in policy_decisions for b in (item.get("blockers") or []) if isinstance(b, str)]
    )
    warnings = _dedupe(
        [str(w) for item in policy_decisions for w in (item.get("warnings") or []) if isinstance(w, str)]
    )

    if not decisions:
        return "unknown", blockers, warnings

    if strategy == "strictest_wins":
        if "blocked" in decisions:
            return "blocked", blockers, warnings
        if all(dec == "pass" for dec in decisions):
            return "pass", blockers, warnings
        if "pass_with_warnings" in decisions:
            return "pass_with_warnings", blockers, warnings
        return "unknown", blockers, warnings

    if strategy == "permissive_preview":
        if "pass" in decisions:
            return "pass", blockers, _dedupe(warnings + blockers)
        if "pass_with_warnings" in decisions:
            return "pass_with_warnings", blockers, _dedupe(warnings + blockers)
        if "blocked" in decisions:
            return "blocked", blockers, warnings
        return "unknown", blockers, warnings

    if strategy == "production_candidate":
        strict = None
        for item in policy_decisions:
            if str(item.get("policy_id") or item.get("policy_name", "")).startswith("strict_gate_policy"):
                strict = str(item.get("decision") or "unknown")
                break
        if strict == "blocked":
            return "blocked", blockers, warnings
        if strict in {"pass", "pass_with_warnings"}:
            if "blocked" in decisions:
                return "pass_with_warnings", blockers, _dedupe(warnings + blockers)
            if "pass_with_warnings" in decisions:
                return "pass_with_warnings", blockers, warnings
            if all(dec == "pass" for dec in decisions):
                return "pass", blockers, warnings
        return "mixed", blockers, warnings

    # compare_all default behavior
    unique = set(decisions)
    if len(unique) == 1:
        return decisions[0], blockers, warnings
    return "mixed", blockers, warnings


def explain_scenario_comparison(result: Dict[str, Any]) -> str:
    decision = result.get("aggregate_decision", "unknown")
    strategy = result.get("comparison_strategy", "compare_all")
    blockers = len(result.get("blockers", [])) if isinstance(result.get("blockers"), list) else 0
    warnings = len(result.get("warnings", [])) if isinstance(result.get("warnings"), list) else 0
    return f"{decision} via {strategy}; blockers={blockers}; warnings={warnings}"


def _aggregate_status_from_decision(decision: str) -> str:
    if decision == "pass":
        return "ready"
    if decision in {"pass_with_warnings", "mixed"}:
        return "review_required"
    if decision == "blocked":
        return "blocked"
    return "unknown"


def _decision_counts(decisions: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for decision in decisions:
        key = str(decision.get("decision") or "unknown")
        counts[key] = counts.get(key, 0) + 1
    return counts


def _dedupe(items: List[str]) -> List[str]:
    seen = set()
    out = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out
