"""Async-safe telemetry tracing with a bounded in-memory ring buffer.

This module is intentionally zero-dependency (stdlib only) and designed for
high-throughput, concurrent event capture under asyncio workloads.

The core abstraction is :class:`TelemetryTracer`, which stores a bounded number
of records (ring-buffer semantics) and can flush a consistent JSON snapshot to
``logs/TELEMETRY_TRACE.json``.
"""

from __future__ import annotations

import json
import os
import time
from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path
from threading import Lock
from typing import Any, Deque, Literal, Mapping, Sequence

from .hashutil import fnv1a_32

PipelineStage = Literal["ISA", "SAS", "CRS", "BOA"]


@dataclass(frozen=True, slots=True)
class TelemetryRecord:
    """Single telemetry trace record captured by the tracer."""

    ts: float
    correlation_id: str
    stage: PipelineStage
    event: str
    payload_bytes: int
    latency_ms: float
    signature: str
    sequence: int


class _RingBufferJSONStream:
    """File-like sink for JSONL governance events that keeps a bounded tail."""

    def __init__(self, *, tracer: "TelemetryTracer") -> None:
        self._tracer = tracer

    def write(self, text: str) -> int:
        # GovernanceLogger writes full JSON lines. Keep it lightweight and
        # tolerant to non-JSON noise.
        line = text.strip()
        if not line:
            return len(text)
        try:
            payload = json.loads(line)
        except Exception:
            return len(text)
        try:
            correlation_id = str(payload.get("correlation_id") or payload.get("handshake_hash") or "unknown")
        except Exception:
            correlation_id = "unknown"
        stage = str(payload.get("source_role") or payload.get("sequence") or "ISA")
        # Coerce to a known stage label when possible, otherwise keep a stable
        # placeholder stage that still passes typing at runtime.
        stage_norm: PipelineStage
        if stage in ("ISA", "SAS", "CRS", "BOA"):
            stage_norm = stage  # type: ignore[assignment]
        else:
            stage_norm = "ISA"
        event = str(payload.get("event") or "GOVERNANCE")
        payload_bytes = len(line.encode("utf-8", errors="replace"))
        self._tracer.record(
            correlation_id=correlation_id,
            stage=stage_norm,
            event=event,
            payload_bytes=payload_bytes,
            latency_ms=0.0,
        )
        return len(text)

    def flush(self) -> None:  # pragma: no cover - used by GovernanceLogger
        return


class TelemetryTracer:
    """High-throughput tracer with bounded in-memory storage.

    The tracer is safe to call concurrently from many asyncio tasks. It avoids
    any `await` on the hot path and uses a minimal locking strategy.
    """

    def __init__(self, *, logs_dir: Path, capacity: int = 4096) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be > 0")
        self._logs_dir = logs_dir
        self._capacity = capacity
        self._lock = Lock()
        self._seq = 0
        self._records: Deque[TelemetryRecord] = deque(maxlen=capacity)

    @property
    def capacity(self) -> int:
        return self._capacity

    def stream(self) -> Any:
        """Return a file-like stream that can be used as a GovernanceLogger sink."""

        return _RingBufferJSONStream(tracer=self)

    def record(
        self,
        *,
        correlation_id: str,
        stage: PipelineStage,
        event: str,
        payload_bytes: int,
        latency_ms: float,
        metadata: Mapping[str, Any] | None = None,
    ) -> TelemetryRecord:
        """Append a telemetry record, evicting the oldest when full."""

        meta = dict(metadata) if metadata else {}
        now = time.time()
        sig_input = json.dumps(
            {
                "correlation_id": correlation_id,
                "stage": stage,
                "event": event,
                "payload_bytes": int(payload_bytes),
                "latency_ms": float(latency_ms),
                "metadata": meta,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        signature = fnv1a_32(sig_input)
        with self._lock:
            self._seq += 1
            rec = TelemetryRecord(
                ts=now,
                correlation_id=str(correlation_id),
                stage=stage,
                event=str(event),
                payload_bytes=int(payload_bytes),
                latency_ms=float(latency_ms),
                signature=signature,
                sequence=self._seq,
            )
            self._records.append(rec)
        return rec

    def snapshot(self) -> list[dict[str, Any]]:
        """Return a JSON-serializable snapshot of current records."""

        with self._lock:
            records: Sequence[TelemetryRecord] = tuple(self._records)
        return [asdict(r) for r in records]

    def flush_trace(self) -> Path:
        """Write an atomic JSON snapshot to ``logs/TELEMETRY_TRACE.json``."""

        payload = self.snapshot()
        self._logs_dir.mkdir(parents=True, exist_ok=True)
        target = self._logs_dir / "TELEMETRY_TRACE.json"
        tmp = self._logs_dir / f".TELEMETRY_TRACE.json.tmp.{os.getpid()}"
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
        tmp.replace(target)
        return target

