from __future__ import annotations

from typing import Any, Dict


def score_finding(finding: Dict[str, Any]) -> Dict[str, int]:
    severity = str(finding.get("severity") or "info").lower()
    category = str(finding.get("category") or "system").lower()
    risk_reduction = {
        "critical": 95,
        "high": 85,
        "medium": 70,
        "low": 55,
        "info": 40,
    }.get(severity, 40)
    effort = {
        "lifecycle": 45,
        "governance": 55,
        "release": 50,
        "memory": 60,
        "scheduler": 60,
        "tooling": 50,
        "repository": 65,
        "system": 45,
    }.get(category, 55)
    confidence = {
        "critical": 90,
        "high": 85,
        "medium": 80,
        "low": 75,
        "info": 70,
    }.get(severity, 70)
    return {
        "risk_reduction_score": int(risk_reduction),
        "effort_score": int(effort),
        "confidence_score": int(confidence),
    }


def derive_priority(*, risk_reduction_score: int, effort_score: int, confidence_score: int) -> str:
    # Higher = more strategic urgency
    urgency = risk_reduction_score + confidence_score - effort_score
    if urgency >= 120:
        return "P0"
    if urgency >= 95:
        return "P1"
    if urgency >= 75:
        return "P2"
    if urgency >= 55:
        return "P3"
    return "P4"


def rank_candidate(candidate: Dict[str, Any]) -> int:
    risk = int(candidate.get("risk_reduction_score") or 0)
    confidence = int(candidate.get("confidence_score") or 0)
    effort = int(candidate.get("effort_score") or 0)
    # Higher rank first.
    return (risk * 2) + confidence - effort

