"""Deterministic workspace engine for the autonomous office runtime."""

from __future__ import annotations

import asyncio
import importlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.exceptions import CriticalMisalignmentError, QuorumDissentException
from core.governance import GovernanceLogger
from core.handshake import run_three_stage_pipeline
from core.recovery import CheckpointManager, CheckpointSnapshot
from core.parsers import (
    DesignatedAgentsConfig,
    RepoGuide,
    load_text,
    parse_agent_guide_list,
    parse_designated_agents_list,
)
from core.types import JSONObject


@dataclass(frozen=True, slots=True)
class WorkspaceState:
    repo_root: Path
    agent_guide_path: Path
    designated_agents_path: Path
    repo_guides: dict[str, RepoGuide]
    designated: DesignatedAgentsConfig

    def snapshot(self) -> JSONObject:
        def _mtime(p: Path) -> float | None:
            try:
                return p.stat().st_mtime
            except OSError:
                return None

        return {
            "repo_root": str(self.repo_root),
            "agent_guide_path": str(self.agent_guide_path),
            "designated_agents_path": str(self.designated_agents_path),
            "agent_guide_mtime": _mtime(self.agent_guide_path),
            "designated_agents_mtime": _mtime(self.designated_agents_path),
            "repo_count": len(self.repo_guides),
            "roles": sorted(self.designated.agents.keys()),
            "default_pipeline": list(self.designated.default_pipeline),
        }


class Orchestrator:
    """Coordinates agent discovery, validation, and pipeline execution."""

    def __init__(self, workspace: WorkspaceState, governance: GovernanceLogger) -> None:
        self.workspace = workspace
        self.governance = governance

    @classmethod
    def load_from_repo_root(cls, repo_root: Path, *, governance: GovernanceLogger) -> "Orchestrator":
        agent_guide_path = repo_root / "AGENT_GUIDE_LIST.md"
        designated_path = repo_root / "DESIGNATED_AGENTS_LIST.md"

        if not agent_guide_path.exists():
            raise FileNotFoundError(str(agent_guide_path))
        if not designated_path.exists():
            raise FileNotFoundError(str(designated_path))

        guides_text = load_text(agent_guide_path)
        designated_text = load_text(designated_path)

        repo_guides = parse_agent_guide_list(guides_text)
        designated = parse_designated_agents_list(designated_text)

        workspace = WorkspaceState(
            repo_root=repo_root,
            agent_guide_path=agent_guide_path,
            designated_agents_path=designated_path,
            repo_guides=repo_guides,
            designated=designated,
        )
        return cls(workspace=workspace, governance=governance)

    async def run(
        self,
        *,
        business_case: str,
        checkpoint: CheckpointManager | None = None,
        resume: CheckpointSnapshot | None = None,
    ) -> int:
        self.governance.emit_event(
            {
                "event": "ORCHESTRATOR_START",
                "cwd": os.getcwd(),
                "workspace": self.workspace.snapshot(),
            }
        )

        try:
            needed_roles = {"intake_specialist", "software_architect", "risk_compliance", "build_orchestrator"}
            if resume is not None:
                if resume.active_stage == "intake_to_architecture":
                    needed_roles.discard("intake_specialist")
                elif resume.active_stage == "architecture_to_risk":
                    needed_roles.discard("intake_specialist")
                    needed_roles.discard("software_architect")
                elif resume.active_stage == "risk_to_build_execution":
                    needed_roles.discard("intake_specialist")
                    needed_roles.discard("software_architect")
                    needed_roles.discard("risk_compliance")
                else:
                    raise CriticalMisalignmentError(f"Unknown resume stage: {resume.active_stage}")
                self.governance.emit_event(
                    {
                        "event": "ORCHESTRATOR_RESUME",
                        "active_stage": resume.active_stage,
                        "schema_id": resume.schema_id,
                        "correlation_id": resume.correlation_id,
                    }
                )

            intake_agent = self._load_agent("intake_specialist") if "intake_specialist" in needed_roles else None
            architect_agent = self._load_agent("software_architect") if "software_architect" in needed_roles else None
            risk_agent = self._load_agent("risk_compliance") if "risk_compliance" in needed_roles else None
            build_agent = self._load_agent("build_orchestrator") if "build_orchestrator" in needed_roles else None

            result = await run_three_stage_pipeline(
                governance=self.governance,
                intake_agent=intake_agent,
                architect_agent=architect_agent,
                risk_agent=risk_agent,
                build_agent=build_agent,
                business_case=business_case,
                workspace_snapshot=self.workspace.snapshot(),
                checkpoint=checkpoint,
                resume=resume,
            )
            self.governance.emit_event({"event": "ORCHESTRATOR_RESULT", "result": result})
            self.governance.set_state("Completed")
            return 0
        except ExceptionGroup as eg:  # pragma: no cover - Python groups TaskGroup errors
            flat: list[BaseException] = []

            def _walk(exc: BaseException) -> None:
                if isinstance(exc, ExceptionGroup):
                    for inner in exc.exceptions:
                        _walk(inner)
                else:
                    flat.append(exc)

            _walk(eg)

            for exc in flat:
                if isinstance(exc, QuorumDissentException):
                    self.governance.emit_event(
                        {
                            "event": "QUORUM_DISSENT",
                            "code": QuorumDissentException.code,
                            "error": str(exc),
                            "stage": getattr(exc, "stage", None),
                            "correlation_id": getattr(exc, "correlation_id", None),
                            "handshake_hash": getattr(exc, "handshake_hash", None),
                            "envelope_signature": getattr(exc, "envelope_signature", None),
                        }
                    )
                    self.governance.set_state("QUORUM_LOCKED_INTERVENTION")
                    return 2
                if isinstance(exc, CriticalMisalignmentError):
                    self.governance.emit_event(
                        {
                            "event": "CRITICAL_MISALIGNMENT",
                            "code": CriticalMisalignmentError.code,
                            "error": str(exc),
                        }
                    )
                    self.governance.set_state("Pending Intervention")
                    return 2
            self.governance.emit_event({"event": "ORCHESTRATOR_ERROR", "error": repr(eg)})
            self.governance.set_state("Pending Intervention")
            return 1
        except QuorumDissentException as e:
            self.governance.emit_event(
                {
                    "event": "QUORUM_DISSENT",
                    "code": QuorumDissentException.code,
                    "error": str(e),
                    "stage": getattr(e, "stage", None),
                    "correlation_id": getattr(e, "correlation_id", None),
                    "handshake_hash": getattr(e, "handshake_hash", None),
                    "envelope_signature": getattr(e, "envelope_signature", None),
                }
            )
            self.governance.set_state("QUORUM_LOCKED_INTERVENTION")
            return 2
        except CriticalMisalignmentError as e:
            self.governance.emit_event(
                {
                    "event": "CRITICAL_MISALIGNMENT",
                    "code": CriticalMisalignmentError.code,
                    "error": str(e),
                }
            )
            self.governance.set_state("Pending Intervention")
            return 2
        except Exception as e:
            self.governance.emit_event({"event": "ORCHESTRATOR_ERROR", "error": repr(e)})
            self.governance.set_state("Pending Intervention")
            return 1

    def _load_agent(self, role: str) -> Any:
        spec = self.workspace.designated.agents.get(role)
        if spec is None:
            raise CriticalMisalignmentError(f"Role missing from designated list: {role}")

        module = importlib.import_module(spec.module)
        cls = getattr(module, spec.class_name, None)
        if cls is None:
            raise CriticalMisalignmentError(f"Agent class not found: {spec.module}.{spec.class_name}")

        # Instantiate with shared workspace/governance context when supported.
        try:
            return cls(workspace=self.workspace, governance=self.governance)
        except TypeError:
            return cls()


def run_sync(
    *,
    business_case: str,
    repo_root: Path,
    governance: GovernanceLogger,
    checkpoint: CheckpointManager | None = None,
    resume: CheckpointSnapshot | None = None,
) -> int:
    orchestrator = Orchestrator.load_from_repo_root(repo_root, governance=governance)
    return asyncio.run(orchestrator.run(business_case=business_case, checkpoint=checkpoint, resume=resume))
