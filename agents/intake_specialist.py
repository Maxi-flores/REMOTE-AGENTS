"""Intake specialist agent.

Responsible for requirement extraction and target repository tokenization.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from core.governance import GovernanceLogger
from core.orchestrator import WorkspaceState
from core.types import JSONObject


@dataclass(slots=True)
class IntakeSpecialist:
    workspace: WorkspaceState
    governance: GovernanceLogger

    async def build_intake_payload(self, *, business_case: str, workspace_snapshot: JSONObject) -> JSONObject:
        targets = self._tokenize_targets(business_case)
        requirements = self._extract_requirements(business_case)

        payload: JSONObject = {
            "business_case": business_case.strip(),
            "target_repositories": targets,
            "requirements": requirements,
            "workspace_snapshot": dict(workspace_snapshot),
        }
        self.governance.emit_event(
            {
                "event": "INTAKE_COMPLETE",
                "target_repositories": targets,
                "requirements_count": len(requirements),
            }
        )
        return payload

    def _tokenize_targets(self, business_case: str) -> list[str]:
        text = business_case.lower()
        discovered: list[str] = []

        # Always include current repo name as a first-class target.
        discovered.append(self.workspace.repo_root.name)

        for repo_name in self.workspace.repo_guides.keys():
            if repo_name.lower() in text:
                discovered.append(repo_name)

        # De-duplicate while preserving order.
        seen: set[str] = set()
        result: list[str] = []
        for name in discovered:
            key = name.strip()
            if not key or key in seen:
                continue
            seen.add(key)
            result.append(key)
        return result

    def _extract_requirements(self, business_case: str) -> list[str]:
        lines = [ln.strip() for ln in business_case.splitlines()]
        reqs: list[str] = []

        bullet_re = re.compile(r"^(?:[-*]|\d+\.)\s+(.+)$")
        for ln in lines:
            if not ln:
                continue
            m = bullet_re.match(ln)
            if m:
                reqs.append(m.group(1).strip())
                continue
            if any(k in ln.lower() for k in ("must", "implement", "create", "ensure", "build")):
                reqs.append(ln)

        if not reqs:
            sentence = business_case.strip().split(".")[0].strip()
            if sentence:
                reqs.append(sentence)

        # Normalize length and de-dup.
        cleaned: list[str] = []
        seen: set[str] = set()
        for r in reqs:
            r2 = re.sub(r"\s+", " ", r).strip()
            if not r2:
                continue
            key = r2.lower()
            if key in seen:
                continue
            seen.add(key)
            cleaned.append(r2)
        return cleaned

