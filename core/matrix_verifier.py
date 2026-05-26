"""Runtime trace verification and pipeline ordering for REMOTE-AGENTS."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any, Iterable, Mapping, Sequence

from .exceptions import PipelineHaltException
from .fault import dump_critical_misalignment
from .telemetry import PipelineStage

_ORDER: tuple[PipelineStage, ...] = ("ISA", "SAS", "CRS", "BOA")
_INDEX: dict[PipelineStage, int] = {name: idx for idx, name in enumerate(_ORDER)}
_HEX32_RE = re.compile(r"^[0-9a-f]{8}$", re.IGNORECASE)


def _is_hex32(token: object) -> bool:
    return isinstance(token, str) and bool(_HEX32_RE.match(token))


@dataclass(frozen=True)
class GovernancePolicy:
    """Deterministic governance policy for ISA -> SAS -> CRS -> BOA transitions."""

    allowed_path: tuple[str, ...]
    source_path: str

    def expected_next(self, from_agent: str) -> str | None:
        try:
            idx = self.allowed_path.index(from_agent)
        except ValueError:
            return None
        if idx + 1 >= len(self.allowed_path):
            return None
        return self.allowed_path[idx + 1]


def load_governance_policy(agent_guide_md: Path, *, repository_name: str | None = None) -> GovernancePolicy:
    """Load governance parameters from AGENT_GUIDE_LIST.md (best-effort)."""
    default = GovernancePolicy(allowed_path=("ISA", "SAS", "CRS", "BOA"), source_path=str(agent_guide_md))
    if not agent_guide_md.exists():
        return default

    if repository_name:
        marker = f"\"repository_name\":\"{repository_name}\""
        try:
            for raw_line in agent_guide_md.read_text(encoding="utf-8", errors="replace").splitlines():
                if marker in raw_line:
                    return GovernancePolicy(allowed_path=default.allowed_path, source_path=str(agent_guide_md))
        except Exception:
            return default
    return default


class MatrixVerifier:
    """Verifier supporting governance path checks and per-correlation ordering."""

    def __init__(self, policy: GovernancePolicy | None = None, *, logs_dir: Path | None = None) -> None:
        self._policy = policy or GovernancePolicy(allowed_path=_ORDER, source_path="default")
        self._last_agent: str | None = None
        self._audited: list[dict[str, str]] = []
        self._logs_dir = logs_dir
        self._lock = Lock()
        self._last_index: dict[str, int] = {}

    @property
    def policy(self) -> GovernancePolicy:
        return self._policy

    def inflight(self) -> int:
        with self._lock:
            return len(self._last_index)

    def verify_transition(
        self,
        *,
        from_agent: str | None = None,
        to_agent: str | None = None,
        correlation_id: str | None = None,
        stage: PipelineStage | str | None = None,
        payload: Mapping[str, Any] | None = None,
    ) -> None:
        if from_agent is not None or to_agent is not None:
            if not from_agent or not to_agent:
                raise PipelineHaltException("Invalid transition: from_agent/to_agent must be non-empty")
            self._verify_governance_transition(from_agent=from_agent, to_agent=to_agent)
            return

        if correlation_id is None or stage is None:
            raise PipelineHaltException("Invalid transition: provide from_agent/to_agent or correlation_id/stage")
        self._verify_stage_transition(correlation_id=correlation_id, stage=stage, payload=payload)

    def _verify_governance_transition(self, *, from_agent: str, to_agent: str) -> None:
        if self._last_agent is None:
            if self._policy.allowed_path and from_agent != self._policy.allowed_path[0]:
                raise PipelineHaltException(
                    f"Governance violation: expected first from_agent={self._policy.allowed_path[0]!r}, got {from_agent!r}"
                )
        else:
            expected_from = self._policy.expected_next(self._last_agent)
            if expected_from is None:
                raise PipelineHaltException(
                    f"Governance violation: unexpected transition after terminal state {self._last_agent!r}"
                )
            if from_agent != expected_from:
                raise PipelineHaltException(
                    f"Governance violation: expected from_agent={expected_from!r} after {self._last_agent!r}, got {from_agent!r}"
                )

        expected_to = self._policy.expected_next(from_agent)
        if expected_to is None:
            raise PipelineHaltException(f"Governance violation: {from_agent!r} cannot transition further")
        if to_agent != expected_to:
            raise PipelineHaltException(
                f"Governance violation: expected {from_agent!r}->{expected_to!r}, got {from_agent!r}->{to_agent!r}"
            )

        self._last_agent = from_agent
        self._audited.append({"from": from_agent, "to": to_agent})

    def _verify_stage_transition(
        self,
        *,
        correlation_id: str,
        stage: PipelineStage | str,
        payload: Mapping[str, Any] | None,
    ) -> None:
        stage_name = str(stage)
        if stage_name not in _INDEX:
            raise PipelineHaltException(f"Unknown pipeline stage: {stage_name!r}")
        observed_idx = _INDEX[stage_name]  # type: ignore[index]
        cid = str(correlation_id)
        with self._lock:
            prior = self._last_index.get(cid, -1)
            expected_idx = prior + 1
            if observed_idx != expected_idx:
                expected = _ORDER[expected_idx] if 0 <= expected_idx < len(_ORDER) else None
                exc = PipelineHaltException(
                    f"Out-of-order pipeline stage for correlation_id={cid!r}: "
                    f"observed={stage_name!r} expected={expected!r}"
                )
                if self._logs_dir is not None:
                    state = {
                        "pipeline_state": "DEAD_HALT",
                        "correlation_id": cid,
                        "observed_stage": stage_name,
                        "expected_stage": expected,
                        "last_index": prior,
                        "observed_index": observed_idx,
                        "payload": dict(payload) if payload else None,
                    }
                    dump_critical_misalignment(self._logs_dir, state, exc)
                raise exc
            self._last_index[cid] = observed_idx
            if stage_name == "BOA":
                self._last_index.pop(cid, None)

    def verify_twin_hash(self, token: object, *, context: str) -> None:
        if not _is_hex32(token):
            raise PipelineHaltException(f"Governance violation: invalid twin hash ({context}): {token!r}")

    def audited_path(self) -> list[dict[str, str]]:
        return list(self._audited)

    def validate_trace_complete(self) -> None:
        if len(self._policy.allowed_path) < 2:
            return
        required_hops = len(self._policy.allowed_path) - 1
        if len(self._audited) != required_hops:
            raise PipelineHaltException(
                f"Governance violation: expected {required_hops} transitions, got {len(self._audited)}"
            )

    def write_telemetry_trace(
        self,
        *,
        logs_dir: Path,
        build_artifact_path: Path,
        micro_log_events: Iterable[dict[str, object]],
        handshake_telemetry: Sequence[dict[str, object]],
        repository_name: str | None = None,
    ) -> Path:
        if not build_artifact_path.exists():
            raise PipelineHaltException(f"Expected build artifact to exist: {build_artifact_path}")
        try:
            artifact_obj = json.loads(build_artifact_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise PipelineHaltException(f"Build artifact is not valid JSON: {build_artifact_path}: {exc!r}") from exc
        if not isinstance(artifact_obj, dict) or artifact_obj.get("status") != "built":
            raise PipelineHaltException(f"Build artifact is not valid/built: {build_artifact_path}")

        self.validate_trace_complete()

        logs_dir.mkdir(parents=True, exist_ok=True)
        out_path = logs_dir / "TELEMETRY_TRACE.json"
        payload = {
            "artifact_path": str(build_artifact_path),
            "repository_name": repository_name,
            "governance_source": self._policy.source_path,
            "allowed_path": list(self._policy.allowed_path),
            "audited_path": self.audited_path(),
            "handshake_telemetry": list(handshake_telemetry),
            "micro_log": list(micro_log_events),
        }
        out_path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
        return out_path
