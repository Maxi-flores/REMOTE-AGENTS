from __future__ import annotations

from typing import Any, Dict, List

from governance_recovery.contracts import GovernanceRecoveryWave, new_id


def group_actions_into_waves(actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    p0p1 = [a for a in actions if isinstance(a, dict) and str(a.get("priority") or "") in {"P0", "P1"}]
    p2 = [a for a in actions if isinstance(a, dict) and str(a.get("priority") or "") == "P2"]
    p3p4 = [a for a in actions if isinstance(a, dict) and str(a.get("priority") or "") in {"P3", "P4"}]

    waves: List[Dict[str, Any]] = []
    if p0p1:
        waves.append(
            GovernanceRecoveryWave(
                wave_id="wave_1",
                title="Wave 1: Readiness and Onboarding Recovery",
                objective="Address highest-impact governance blockers first.",
                priority="P1",
                actions=[str(a.get("action_id")) for a in p0p1],
                expected_score_impact=_impact_sum(p0p1),
                advisory_only=True,
                metadata={},
            ).to_dict()
        )
    if p2:
        waves.append(
            GovernanceRecoveryWave(
                wave_id="wave_2",
                title="Wave 2: Dependency and Critical-Path Stabilization",
                objective="Reduce elevated governance and dependency risk.",
                priority="P2",
                actions=[str(a.get("action_id")) for a in p2],
                expected_score_impact=_impact_sum(p2),
                advisory_only=True,
                metadata={},
            ).to_dict()
        )
    if p3p4:
        waves.append(
            GovernanceRecoveryWave(
                wave_id="wave_3",
                title="Wave 3: Drift Cleanup and Trend Hardening",
                objective="Stabilize governance baselines and monitoring confidence.",
                priority="P3",
                actions=[str(a.get("action_id")) for a in p3p4],
                expected_score_impact=_impact_sum(p3p4),
                advisory_only=True,
                metadata={},
            ).to_dict()
        )
    return waves


def _impact_sum(actions: List[Dict[str, Any]]) -> int:
    return int(sum(int(a.get("expected_score_impact") or 0) for a in actions if isinstance(a, dict)))

