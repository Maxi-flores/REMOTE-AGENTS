"""Software architect agent.

Responsible for dependency matching and code impact assessment.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.governance import GovernanceLogger
from core.handshake import PacketEnvelope
from core.orchestrator import WorkspaceState
from core.types import JSONObject


@dataclass(slots=True)
class SoftwareArchitect:
    workspace: WorkspaceState
    governance: GovernanceLogger

    async def build_architecture_payload(self, *, intake_envelope: PacketEnvelope[JSONObject]) -> JSONObject:
        intake = intake_envelope.payload
        targets = list(intake["target_repositories"]) if isinstance(intake.get("target_repositories"), list) else []
        requirements = list(intake["requirements"]) if isinstance(intake.get("requirements"), list) else []

        plan = self._draft_plan(requirements=requirements)
        impact = {
            "touched_components": [
                "core/orchestrator.py",
                "core/handshake.py",
                "core/governance.py",
                "agents/*",
                "config/manifests/*",
            ],
            "determinism_notes": [
                "Canonical JSON hashing for signatures",
                "Single-item queues for stage boundaries",
            ],
        }

        payload: JSONObject = {
            "target_repositories": targets,
            "architecture_plan": plan,
            "impact_assessment": impact,
            "trace": {"intake_signature": intake_envelope.signature},
        }
        self.governance.emit_event(
            {
                "event": "ARCHITECTURE_COMPLETE",
                "target_repositories": targets,
                "plan_steps": len(plan),
            }
        )
        return payload

    def _draft_plan(self, *, requirements: list[str]) -> list[str]:
        if requirements:
            return [f"Address requirement: {r}" for r in requirements[:12]]
        return [
            "Parse governance markdown inputs",
            "Validate and sign handshake payloads",
            "Run staged pipeline with audit logging",
        ]

