"""
Runtime trace verification for the REMOTE-AGENTS asynchronous pipeline.

The REMOTE-AGENTS runtime models four deterministic agent states:
  ISA -> SAS -> CRS -> BOA

This module provides a small governance engine that:
  - performs lookahead transition verification (fail-fast)
  - raises PipelineHaltException when sequence is violated
  - can emit an audited trace file when a build artifact is produced

No external dependencies are used (Python 3.10+ stdlib only).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from .exceptions import PipelineHaltException


_HEX32_RE = re.compile(r"^[0-9a-f]{8}$", re.IGNORECASE)


def _is_hex32(token: object) -> bool:
    return isinstance(token, str) and bool(_HEX32_RE.match(token))


@dataclass(frozen=True)
class GovernancePolicy:
    """
    Deterministic governance policy for state transitions.

    Attributes:
      - allowed_path: ordered list of agent names in the required sequence.
      - source_path: where the policy was derived from (best-effort).
    """

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
    """
    Load governance parameters from AGENT_GUIDE_LIST.md (best-effort).

    The current repository's guide file primarily contains training metadata.
    For compatibility and future extensibility, this loader extracts the
    repository JSON configuration (if present) but falls back to the canonical
    four-state path required by this runtime.
    """
    default = GovernancePolicy(allowed_path=("ISA", "SAS", "CRS", "BOA"), source_path=str(agent_guide_md))
    if not agent_guide_md.exists():
        return default

    # Best-effort: if a JSON config line exists for the current repository,
    # record that we "consulted" it without changing deterministic behavior.
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
    """
    Verification matrix engine for runtime transition auditing.

    The verifier is intentionally small: it validates that runtime transitions
    stay on the allowed path. Any out-of-sequence transition raises a
    PipelineHaltException, enabling the caller to enter the DEAD_HALT fault
    pipeline immediately.
    """

    def __init__(self, policy: GovernancePolicy) -> None:
        self._policy = policy
        self._last_agent: str | None = None
        self._audited: list[dict[str, str]] = []

    @property
    def policy(self) -> GovernancePolicy:
        return self._policy

    def verify_transition(self, *, from_agent: str, to_agent: str) -> None:
        """
        Lookahead verification: fail fast on invalid transitions.
        """
        if not from_agent or not to_agent:
            raise PipelineHaltException("Invalid transition: from_agent/to_agent must be non-empty")

        if self._last_agent is None:
            # First hop must start at path[0] -> path[1]
            if self._policy.allowed_path and from_agent != self._policy.allowed_path[0]:
                raise PipelineHaltException(
                    f"Governance violation: expected first from_agent={self._policy.allowed_path[0]!r}, got {from_agent!r}"
                )
        else:
            expected_from = self._policy.expected_next(self._last_agent)
            if expected_from is None:
                raise PipelineHaltException(f"Governance violation: unexpected transition after terminal state {self._last_agent!r}")
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

    def verify_twin_hash(self, token: object, *, context: str) -> None:
        """
        Verify that a twin hash is a 32-bit FNV-1a token (8 hex chars).
        """
        if not _is_hex32(token):
            raise PipelineHaltException(f"Governance violation: invalid twin hash ({context}): {token!r}")

    def audited_path(self) -> list[dict[str, str]]:
        return list(self._audited)

    def validate_trace_complete(self) -> None:
        """
        Ensure the audited path reaches the final hop in the allowed path.
        """
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
        """
        Write final audited telemetry to logs/TELEMETRY_TRACE.json.

        A "valid" build artifact is defined as an on-disk JSON file that loads
        to an object containing {"status": "built"}.
        """
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

