"""Risk and compliance agent.

Responsible for automated threat simulation and strict rule validation loops.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.governance import GovernanceLogger
from core.handshake import PacketEnvelope
from core.orchestrator import WorkspaceState
from core.types import JSONObject


@dataclass(slots=True)
class RiskCompliance:
    workspace: WorkspaceState
    governance: GovernanceLogger

    async def build_risk_payload(self, *, architecture_envelope: PacketEnvelope[JSONObject]) -> JSONObject:
        arch = architecture_envelope.payload
        targets = list(arch["target_repositories"]) if isinstance(arch.get("target_repositories"), list) else []

        risk_summary = self._simulate_risks(architecture_payload=arch)
        compliance_status = "pass" if not any("blocker:" in r.lower() for r in risk_summary) else "fail"
        recommended_actions = self._recommend_actions(compliance_status=compliance_status, risks=risk_summary)

        payload: JSONObject = {
            "target_repositories": targets,
            "compliance_status": compliance_status,
            "risk_summary": risk_summary,
            "recommended_actions": recommended_actions,
            "trace": {"architecture_signature": architecture_envelope.signature},
        }
        self.governance.emit_event(
            {
                "event": "RISK_COMPLETE",
                "target_repositories": targets,
                "compliance_status": compliance_status,
            }
        )
        return payload

    def _simulate_risks(self, *, architecture_payload: JSONObject) -> list[str]:
        risks: list[str] = []
        plan = architecture_payload.get("architecture_plan")
        if isinstance(plan, list) and len(plan) > 20:
            risks.append("Potential scope creep: architecture plan is large.")
        risks.append("Validate handshake payloads reject unexpected keys (strict schema).")
        risks.append("Ensure governance logs do not record secrets or tokens.")
        return risks

    def _recommend_actions(self, *, compliance_status: str, risks: list[str]) -> list[str]:
        actions = [
            "Run a smoke execution of run_autonomous_office.py with a short business case.",
            "Review governance.jsonl for CRITICAL_MISALIGNMENT events.",
        ]
        if compliance_status != "pass":
            actions.insert(0, "Blocker: remediate compliance failures before execution.")
        return actions

