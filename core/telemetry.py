"""
Asynchronous, zero-dependency telemetry collection for the REMOTE-AGENTS runtime.

This module provides a lightweight in-memory trace buffer designed for runtime
inspection without altering payload schemas or queue behavior.

Design goals:
  - stdlib-only (Python 3.10+)
  - deterministic, flat micro-log events
  - bounded memory via a ring buffer
  - safe to call from asyncio pipelines with minimal overhead
"""

from __future__ import annotations

import asyncio
import json
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Deque, Iterable, Mapping, MutableMapping


MicroLogEvent = dict[str, object]
TelemetryHook = Callable[[MicroLogEvent], object]


def _utc_iso_seconds() -> str:
    """
    Return a stable, second-resolution UTC timestamp.

    The rest of the system formatter uses second-resolution UTC timestamps; we
    match that resolution to keep trace output consistent and compact.
    """
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _latency_ms(start_monotonic: float, end_monotonic: float) -> float:
    ms = (end_monotonic - start_monotonic) * 1000.0
    if ms < 0:
        return 0.0
    return round(ms, 3)


def estimate_payload_bytes(payload: object) -> int:
    """
    Estimate payload size in bytes without mutating it.

    - dict/list/str/int/float/bool/None are converted through JSON for a stable
      estimate (sorted keys, compact separators).
    - bytes/bytearray sizes are measured directly.
    - unknown objects fall back to repr().
    """
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
    """
    Internal record linking a queued object identity to its enqueue timestamp.
    """

    queue_name: str
    enqueued_at: float
    src_agent: str | None
    dst_agent: str | None


class TelemetryTracker:
    """
    Async telemetry tracker using an in-memory ring buffer.

    Each stored event is a strictly flat dictionary. The following keys are
    always present:
      - component: str
      - twin_hash: str
      - event_type: str
      - latency_ms: float

    Additional fields (flat) may be present (timestamp, src/dst agent, queue,
    payload_bytes, error, etc.).

    Hooks:
      - Call `add_hook()` with a callable that accepts an event dict.
      - If the hook returns an awaitable, it is scheduled via create_task().
      - Hook failures are swallowed to avoid impacting pipeline correctness.
    """

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
        """
        Append a micro-log event to the ring buffer and dispatch hooks.
        """
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
        """
        Mark the enqueue time for an item within a named queue.

        The mark is keyed by (queue_name, id(item)) and is bounded to avoid
        memory growth if unexpected queue usage occurs.
        """
        key = (queue_name, id(item))
        async with self._lock:
            if len(self._queue_marks) >= self._max_queue_marks:
                # Drop an arbitrary mark to protect memory boundaries.
                self._queue_marks.pop(next(iter(self._queue_marks)), None)
            self._queue_marks[key] = QueueMark(queue_name=queue_name, enqueued_at=time.monotonic(), src_agent=src_agent, dst_agent=dst_agent)

    async def pop_enqueue_latency_ms(self, *, queue_name: str, item: object) -> tuple[float | None, QueueMark | None]:
        """
        Return queue wait latency for an item and remove its mark if present.
        """
        key = (queue_name, id(item))
        async with self._lock:
            mark = self._queue_marks.pop(key, None)
        if not mark:
            return None, None
        return _latency_ms(mark.enqueued_at, time.monotonic()), mark

    async def snapshot(self) -> list[MicroLogEvent]:
        """
        Return a stable list copy of the current buffer contents.
        """
        async with self._lock:
            return list(self._buffer)

    async def flush_json(self, path: Path, *, events: Iterable[MicroLogEvent] | None = None) -> Path:
        """
        Write telemetry events to JSON on disk.
        """
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
            # Not in an event loop; run hooks synchronously.
            loop = None

        for hook in list(self._hooks):
            try:
                result = hook(event)
                if loop is not None and asyncio.iscoroutine(result):
                    loop.create_task(result)  # fire-and-forget
            except Exception:
                # Telemetry must never break pipeline semantics.
                continue

