from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from release_gates.contracts import GateDecision, new_id
from release_gates.policy_loader import load_named_gate_policy


def simulate_gate(report: Dict[str, Any], policy: Dict[str, Any]) -> Dict[str, Any]:
    readiness_score = float(report.get("readiness_score") or 0)
    blockers = list(report.get("blockers") or [])
    warnings = list(report.get("warnings") or [])
    findings = list(report.get("findings") or [])
    checked_artifacts = list(report.get("checked_artifacts") or [])

    artifacts_present = {
        str(entry.get("artifact_type"))
        for entry in checked_artifacts
        if isinstance(entry, dict) and isinstance(entry.get("artifact_type"), str)
    }
    decision_blockers = list(blockers)
    decision_warnings = list(warnings)

    if readiness_score < float(policy.get("minimum_readiness_score", 100)):
        decision_blockers.append(
            f"readiness_score {readiness_score} below minimum {policy.get('minimum_readiness_score')}"
        )

    if policy.get("block_on_critical_findings"):
        critical = [f for f in findings if isinstance(f, dict) and f.get("severity") == "critical"]
        if critical:
            decision_blockers.append("critical findings present")

    def _has_drift(drift_type: str) -> bool:
        return any(isinstance(f, dict) and f.get("drift_type") == drift_type for f in findings)

    if policy.get("block_on_malformed_artifacts") and _has_drift("malformed_artifact"):
        decision_blockers.append("malformed artifacts present")
    if policy.get("block_on_missing_artifacts") and _has_drift("missing_artifact"):
        decision_blockers.append("missing artifacts present")
    if policy.get("block_on_unsupported_versions") and _has_drift("unsupported_version"):
        decision_blockers.append("unsupported versions present")

    if len(decision_warnings) > int(policy.get("max_warning_count", 0)):
        decision_blockers.append("warning count exceeds policy threshold")
    error_count = sum(1 for f in findings if isinstance(f, dict) and f.get("severity") in {"error", "critical"})
    if error_count > int(policy.get("max_error_count", 0)):
        decision_blockers.append("error count exceeds policy threshold")

    required_artifacts = [str(v) for v in policy.get("required_artifacts", []) if isinstance(v, str)]
    missing_required = [artifact for artifact in required_artifacts if artifact not in artifacts_present]
    if missing_required:
        decision_blockers.append(f"required artifacts missing: {', '.join(missing_required)}")

    if len(checked_artifacts) == 0:
        decision = "unknown"
    elif decision_blockers:
        decision = "blocked"
    elif decision_warnings:
        decision = "pass_with_warnings"
    else:
        decision = "pass"

    gate_decision = GateDecision(
        decision_id=new_id("gate_decision"),
        policy_id=str(policy.get("policy_id") or "unknown_policy"),
        report_id=report.get("report_id") if isinstance(report.get("report_id"), str) else None,
        decision=decision,  # type: ignore[arg-type]
        readiness_score=readiness_score,
        blockers=_dedupe(decision_blockers),
        warnings=_dedupe(decision_warnings),
        evaluated_artifacts=checked_artifacts,
        advisory_only=bool(policy.get("advisory_only", True)),
        metadata={"advisory_only": bool(policy.get("advisory_only", True))},
    )
    return gate_decision.to_dict()


def simulate_gate_from_report_file(
    report_path: str | Path = ".release_reports/release_readiness.json",
    policy_name: str = "default_gate_policy",
) -> Dict[str, Any]:
    path = Path(report_path)
    if not path.exists():
        report = {
            "report_id": None,
            "readiness_score": 0,
            "blockers": ["release readiness report missing"],
            "warnings": [],
            "findings": [],
            "checked_artifacts": [],
        }
    else:
        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        report = payload if isinstance(payload, dict) else {}
    policy = load_named_gate_policy(policy_name)
    return simulate_gate(report, policy)


def explain_gate_decision(decision: Dict[str, Any]) -> str:
    gate = str(decision.get("decision") or "unknown")
    score = decision.get("readiness_score")
    blockers = decision.get("blockers") if isinstance(decision.get("blockers"), list) else []
    if blockers:
        return f"{gate}: score={score}; blockers={len(blockers)}"
    warnings = decision.get("warnings") if isinstance(decision.get("warnings"), list) else []
    return f"{gate}: score={score}; warnings={len(warnings)}"


def _dedupe(items: List[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out

