from __future__ import annotations

from typing import Any, Dict


def score_finding(finding: Dict[str, Any]) -> Dict[str, int]:
    severity = str(finding.get("severity") or "info").lower()
    category = str(finding.get("category") or "observability").lower()
    risk_score = {
        "critical": 95,
        "high": 85,
        "medium": 70,
        "low": 50,
        "info": 35,
    }.get(severity, 35)
    effort_score = {
        "runtime": 70,
        "contracts": 45,
        "config": 40,
        "tests": 50,
        "docs": 30,
        "governance": 55,
        "lifecycle": 50,
        "release": 55,
        "observability": 40,
    }.get(category, 45)
    confidence_score = {
        "critical": 90,
        "high": 85,
        "medium": 80,
        "low": 75,
        "info": 70,
    }.get(severity, 70)
    return {
        "risk_score": int(risk_score),
        "effort_score": int(effort_score),
        "confidence_score": int(confidence_score),
    }


def derive_priority(*, risk_score: int, effort_score: int, confidence_score: int) -> str:
    pressure = risk_score + confidence_score - effort_score
    if pressure >= 120:
        return "P0"
    if pressure >= 95:
        return "P1"
    if pressure >= 75:
        return "P2"
    if pressure >= 55:
        return "P3"
    return "P4"


def rank_item(item: Dict[str, Any]) -> int:
    return (int(item.get("risk_score") or 0) * 2) + int(item.get("confidence_score") or 0) - int(
        item.get("effort_score") or 0
    )
