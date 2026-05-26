"""Lookahead pipeline sequence verifier.

The verifier enforces a strict transition order across the execution pipeline:
``ISA -> SAS -> CRS -> BOA``.

It is intentionally lightweight and stdlib-only to support stress testing and
high concurrency. On an out-of-order transition, it raises
``core.exceptions.PipelineHaltException`` and writes ``logs/CRITICAL_MISALIGNMENT.json``
via ``core.fault.dump_critical_misalignment``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any, Mapping

from .exceptions import PipelineHaltException
from .fault import dump_critical_misalignment
from .telemetry import PipelineStage

_ORDER: tuple[PipelineStage, ...] = ("ISA", "SAS", "CRS", "BOA")
_INDEX: dict[PipelineStage, int] = {name: idx for idx, name in enumerate(_ORDER)}


@dataclass(slots=True)
class MatrixVerifier:
    """Stateful verifier enforcing strict stage ordering per correlation id."""

    logs_dir: Path

    _lock: Lock = field(init=False, repr=False)
    _last_index: dict[str, int] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._lock = Lock()
        self._last_index = {}

    def inflight(self) -> int:
        with self._lock:
            return len(self._last_index)

    def verify_transition(
        self,
        *,
        correlation_id: str,
        stage: PipelineStage,
        payload: Mapping[str, Any] | None = None,
    ) -> None:
        """Validate transition order, raising on out-of-order stage emission."""

        cid = str(correlation_id)
        observed_idx = _INDEX[stage]
        with self._lock:
            prior = self._last_index.get(cid, -1)
            expected_idx = prior + 1
            if observed_idx != expected_idx:
                expected = _ORDER[expected_idx] if 0 <= expected_idx < len(_ORDER) else None
                exc = PipelineHaltException(
                    f"Out-of-order pipeline stage for correlation_id={cid!r}: "
                    f"observed={stage!r} expected={expected!r}"
                )
                state = {
                    "pipeline_state": "DEAD_HALT",
                    "correlation_id": cid,
                    "observed_stage": stage,
                    "expected_stage": expected,
                    "last_index": prior,
                    "observed_index": observed_idx,
                    "payload": dict(payload) if payload else None,
                }
                dump_critical_misalignment(self.logs_dir, state, exc)
                raise exc
            self._last_index[cid] = observed_idx
            if stage == "BOA":
                self._last_index.pop(cid, None)
