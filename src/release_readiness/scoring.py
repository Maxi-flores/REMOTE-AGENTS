from __future__ import annotations

from typing import Any, Dict, List

from release_readiness.contracts import ReleaseReadinessReport, new_id, utc_now


def score_findings(findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    score = 100.0
    blockers: List[str] = []
    warnings: List[str] = []
    for finding in findings:
        severity = str(finding.get("severity") or "info")
        drift_type = str(finding.get("drift_type") or "")
        message = str(finding.get("message") or "")
        if severity == "warning":
            score -= 5
            warnings.append(message)
        elif severity == "error":
            score -= 20
            warnings.append(message)
        elif severity == "critical":
            score -= 50
            blockers.append(message)
        if drift_type in {"missing_artifact", "malformed_artifact", "unsupported_version"}:
            blockers.append(message)
        if drift_type == "deprecated_version":
            warnings.append(message)
    score = max(0.0, min(100.0, score))
    return {"score": score, "blockers": _dedupe(blockers), "warnings": _dedupe(warnings)}


def classify_readiness(score: float, blockers: List[str]) -> str:
    if len(blockers) > 0 or score < 70:
        return "blocked"
    if score >= 90:
        return "ready"
    if score >= 70:
        return "ready_with_warnings"
    return "unknown"


def build_release_readiness_report(
    scope: str = "sentient-control-plane",
    findings: List[Dict[str, Any]] | None = None,
    checked_artifacts: List[Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    findings = findings or []
    checked_artifacts = checked_artifacts or []
    scored = score_findings(findings)
    score = float(scored["score"])
    blockers = list(scored["blockers"])
    warnings = list(scored["warnings"])
    status = classify_readiness(score, blockers)
    if len(checked_artifacts) == 0 and len(findings) == 0:
        status = "unknown"
    report = ReleaseReadinessReport(
        report_id=new_id("release_readiness"),
        generated_utc=utc_now(),
        scope=scope,
        readiness_score=score,
        readiness_status=status,  # type: ignore[arg-type]
        blockers=blockers,
        warnings=warnings,
        findings=findings,
        checked_artifacts=checked_artifacts,
        summary={
            "finding_count": len(findings),
            "blocker_count": len(blockers),
            "warning_count": len(warnings),
            "checked_artifact_count": len(checked_artifacts),
        },
        metadata={"advisory_only": True},
    )
    return report.to_dict()


def _dedupe(items: List[str]) -> List[str]:
    seen = set()
    out = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out

