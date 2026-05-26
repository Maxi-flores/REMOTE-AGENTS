"""Telemetry utilities for the REMOTE-AGENTS runtime.

This module keeps both telemetry paths that exist in the codebase:
- TelemetryTracker: async-safe micro-log ring buffer used by the ISA/SAS/CRS/BOA
  pipeline for per-event tracing and queue latency measurement.
- TelemetryTracer: synchronous, high-throughput tracer used by stress rigs and
  governance streams for compact JSON snapshots.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path
from threading import Lock
from typing import Any, Callable, Deque, Iterable, Literal, Mapping, MutableMapping, Sequence

from .hashutil import fnv1a_32

PipelineStage = Literal["ISA", "SAS", "CRS", "BOA"]

MicroLogEvent = dict[str, object]
TelemetryHook = Callable[[MicroLogEvent], object]


def _utc_iso_seconds() -> str:
    """Return a stable, second-resolution UTC timestamp."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _latency_ms(start_monotonic: float, end_monotonic: float) -> float:
    ms = (end_monotonic - start_monotonic) * 1000.0
    if ms < 0:
        return 0.0
    return round(ms, 3)


def estimate_payload_bytes(payload: object) -> int:
    """Estimate payload size in bytes without mutating it."""
    if payload is None:
        return 0
    if isinstance(payload, (bytes, bytearray)):
        return len(payload)
    try:
        blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    except Exception:
        blob = repr(payload)
    return len(blob.encode("utf-8", errors="surrogatepass"))


@dataclass(frozen=True)
class QueueMark:
    """Internal record linking a queued object identity to its enqueue timestamp."""

    queue_name: str
    enqueued_at: float
    src_agent: str | None
    dst_agent: str | None


class TelemetryTracker:
    """Async telemetry tracker using an in-memory ring buffer."""

    def __init__(self, *, max_events: int = 1024) -> None:
        if max_events <= 0:
            raise ValueError("max_events must be positive")
        self._buffer: Deque[MicroLogEvent] = deque(maxlen=max_events)
        self._lock = asyncio.Lock()
        self._hooks: list[TelemetryHook] = []
        self._queue_marks: MutableMapping[tuple[str, int], QueueMark] = {}
        self._max_queue_marks = min(4096, max_events * 4)

    def add_hook(self, hook: TelemetryHook) -> None:
        self._hooks.append(hook)

    async def record(
        self,
        *,
        component: str,
        event_type: str,
        twin_hash: str = "-",
        latency_ms: float = 0.0,
        timestamp_utc: str | None = None,
        src_agent: str | None = None,
        dst_agent: str | None = None,
        payload_bytes: int | None = None,
        extra: Mapping[str, object] | None = None,
    ) -> MicroLogEvent:
        """Append a micro-log event to the ring buffer and dispatch hooks."""
        event: MicroLogEvent = {
            "component": component,
            "twin_hash": twin_hash,
            "event_type": event_type,
            "latency_ms": float(latency_ms),
            "ts_utc": timestamp_utc or _utc_iso_seconds(),
        }
        if src_agent is not None:
            event["src_agent"] = src_agent
        if dst_agent is not None:
            event["dst_agent"] = dst_agent
        if payload_bytes is not None:
            event["payload_bytes"] = int(payload_bytes)
        if extra:
            for k, v in extra.items():
                if k in event:
                    continue
                if isinstance(k, str):
                    event[k] = v

        async with self._lock:
            self._buffer.append(event)

        self._dispatch_hooks(event)
        return event

    async def mark_enqueue(
        self,
        *,
        queue_name: str,
        item: object,
        src_agent: str | None = None,
        dst_agent: str | None = None,
    ) -> None:
        """Mark the enqueue time for an item within a named queue."""
        key = (queue_name, id(item))
        async with self._lock:
            if len(self._queue_marks) >= self._max_queue_marks:
                self._queue_marks.pop(next(iter(self._queue_marks)), None)
            self._queue_marks[key] = QueueMark(
                queue_name=queue_name,
                enqueued_at=time.monotonic(),
                src_agent=src_agent,
                dst_agent=dst_agent,
            )

    async def pop_enqueue_latency_ms(self, *, queue_name: str, item: object) -> tuple[float | None, QueueMark | None]:
        """Return queue wait latency for an item and remove its mark if present."""
        key = (queue_name, id(item))
        async with self._lock:
            mark = self._queue_marks.pop(key, None)
        if not mark:
            return None, None
        return _latency_ms(mark.enqueued_at, time.monotonic()), mark

    async def snapshot(self) -> list[MicroLogEvent]:
        """Return a stable list copy of the current buffer contents."""
        async with self._lock:
            return list(self._buffer)

    async def flush_json(self, path: Path, *, events: Iterable[MicroLogEvent] | None = None) -> Path:
        """Write telemetry events to JSON on disk."""
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = list(events) if events is not None else await self.snapshot()
        path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
        return path

    def _dispatch_hooks(self, event: MicroLogEvent) -> None:
        if not self._hooks:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        for hook in list(self._hooks):
            try:
                result = hook(event)
                if loop is not None and asyncio.iscoroutine(result):
                    loop.create_task(result)
            except Exception:
                continue


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
    """High-throughput tracer with bounded in-memory storage."""

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
