"""Async event ingestion gateway (stdlib-only).

Exposes:
  - POST /api/v1/trigger  (enqueue instruction payloads)
  - GET  /health          (compute + queue telemetry)
  - GET  /ws/events       (WebSocket text frames -> enqueue)

This gateway intentionally integrates with the existing disk queue contract:
tasks are flushed one-at-a-time to `.platform_queue/next_task.json` only when
the worker is idle. Excess triggers remain in-memory to reduce SSD churn.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from tools.logger import ensure_runtime_directories  # noqa: E402
from tools.semantic_memory import memory_counts_by_repository  # noqa: E402
from tools.workspace_mounter import workspace_dir_health  # noqa: E402


PLATFORM_TASK_FILE = Path(".platform_queue/next_task.json")
PLATFORM_LOCK_FILE = Path(".platform_queue/processing.lock")
CONSENSUS_METRICS_FILE = Path(".logs/consensus_metrics.json")

_WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


def _utc_ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _json_bytes(obj: Any) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, indent=2) + "\n").encode("utf-8", errors="strict")


def _readable_duration_s(age_s: float | None) -> float | None:
    if age_s is None:
        return None
    return float(round(float(age_s), 3))


def _parse_instruction_payload(raw: bytes) -> tuple[str, int, str | None]:
    try:
        obj = json.loads(raw.decode("utf-8", errors="strict"))
    except Exception as exc:
        raise ValueError(f"invalid JSON: {exc}") from exc
    if not isinstance(obj, dict):
        raise ValueError("payload must be a JSON object")
    instruction = obj.get("instruction")
    if not isinstance(instruction, str) or not instruction.strip():
        raise ValueError('payload must contain {"instruction": "string"}')
    priority = obj.get("priority", 0)
    if priority is None:
        priority = 0
    if not isinstance(priority, int) or isinstance(priority, bool):
        raise ValueError("priority must be an integer")
    target_repository = obj.get("target_repository")
    if not isinstance(target_repository, str) or not target_repository.strip():
        target_repository = None
    else:
        target_repository = target_repository.strip()
    return instruction, int(priority), target_repository


def _read_processing_lock_details() -> dict[str, Any] | None:
    try:
        raw = PLATFORM_LOCK_FILE.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    try:
        obj = json.loads(raw)
    except Exception:
        return {"raw": raw[:4096]}
    if isinstance(obj, dict):
        return obj
    return {"raw": raw[:4096]}


def _system_memory_metrics() -> dict[str, Any]:
    total_bytes: int | None = None
    available_bytes: int | None = None
    used_bytes: int | None = None
    used_percent: float | None = None
    process_rss_bytes: int | None = None

    # System totals (best-effort; cross-platform, stdlib-only).
    try:
        if sys.platform.startswith("linux") and os.path.exists("/proc/meminfo"):
            meminfo: dict[str, int] = {}
            with open("/proc/meminfo", "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if ":" not in line:
                        continue
                    k, v = line.split(":", 1)
                    parts = v.strip().split()
                    if not parts:
                        continue
                    try:
                        meminfo[k] = int(parts[0]) * 1024  # kB -> bytes
                    except Exception:
                        continue
            total_bytes = meminfo.get("MemTotal")
            available_bytes = meminfo.get("MemAvailable") or meminfo.get("MemFree")
    except Exception:
        pass

    if total_bytes is None:
        try:
            page_size = int(os.sysconf("SC_PAGE_SIZE"))
            phys_pages = int(os.sysconf("SC_PHYS_PAGES"))
            total_bytes = page_size * phys_pages
        except Exception:
            pass

    if total_bytes is not None and available_bytes is not None:
        used_bytes = max(0, int(total_bytes) - int(available_bytes))
        used_percent = round((float(used_bytes) / float(total_bytes)) * 100.0, 2)

    # Process RSS (fallback when system availability isn't accessible).
    try:
        if sys.platform.startswith("linux") and os.path.exists("/proc/self/statm"):
            with open("/proc/self/statm", "r", encoding="utf-8", errors="replace") as f:
                parts = f.read().strip().split()
            if parts:
                rss_pages = int(parts[1])
                page_size = int(os.sysconf("SC_PAGE_SIZE"))
                process_rss_bytes = rss_pages * page_size
    except Exception:
        pass

    if process_rss_bytes is None:
        try:
            import resource

            ru = resource.getrusage(resource.RUSAGE_SELF)
            # Linux: kilobytes, macOS: bytes. Heuristic: treat small values as kB.
            rss = int(getattr(ru, "ru_maxrss", 0))
            if rss > 0:
                process_rss_bytes = rss if rss > 10_000_000 else rss * 1024
        except Exception:
            pass

    return {
        "system_total_bytes": total_bytes,
        "system_available_bytes": available_bytes,
        "system_used_bytes": used_bytes,
        "system_used_percent": used_percent,
        "process_rss_bytes": process_rss_bytes,
    }


def _consensus_metrics() -> dict[str, int]:
    try:
        raw = CONSENSUS_METRICS_FILE.read_text(encoding="utf-8", errors="replace")
    except OSError:
        raw = ""
    try:
        obj = json.loads(raw) if raw else {}
    except Exception:
        obj = {}
    if not isinstance(obj, dict):
        obj = {}
    return {
        "total_consensus_reviews": int(obj.get("total_consensus_reviews") or 0),
        "twin_rejections": int(obj.get("twin_rejections") or 0),
        "successful_refinements": int(obj.get("successful_refinements") or 0),
    }


def _semantic_memory_metrics() -> dict[str, Any]:
    try:
        by_repo = memory_counts_by_repository()
    except Exception:
        by_repo = {}

    flat: dict[str, int] = {}
    for repo_name, count in sorted(by_repo.items(), key=lambda t: t[0].lower()):
        safe = "".join(ch if (ch.isalnum() or ch == "_") else "_" for ch in str(repo_name))
        flat[f"{safe}_memories_count"] = int(count)

    return {
        "total_records": int(sum(int(v) for v in by_repo.values())),
        "by_repository": {str(k): int(v) for k, v in by_repo.items()},
        "flat_counts": flat,
    }


def _ws_accept_value(key: str) -> str:
    raw = (key + _WS_GUID).encode("ascii", errors="strict")
    digest = hashlib.sha1(raw).digest()
    return base64.b64encode(digest).decode("ascii")


async def _read_http_headers(reader: asyncio.StreamReader, *, limit: int = 64 * 1024) -> list[str]:
    raw = await reader.readuntil(b"\r\n\r\n")
    if len(raw) > limit:
        raise ValueError("header too large")
    text = raw.decode("latin-1", errors="replace")
    return [line for line in text.split("\r\n") if line]


def _parse_headers(lines: list[str]) -> tuple[str, str, dict[str, str]]:
    if not lines:
        raise ValueError("empty request")
    parts = lines[0].split()
    if len(parts) < 2:
        raise ValueError("bad request line")
    method = parts[0].upper()
    path = parts[1]
    headers: dict[str, str] = {}
    for line in lines[1:]:
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        headers[k.strip().lower()] = v.strip()
    return method, path, headers


def _http_response(status: int, body: bytes, *, content_type: str = "application/json") -> bytes:
    reason = {
        200: "OK",
        202: "Accepted",
        400: "Bad Request",
        404: "Not Found",
        405: "Method Not Allowed",
        500: "Internal Server Error",
        101: "Switching Protocols",
    }.get(int(status), "OK")
    headers = [
        f"HTTP/1.1 {int(status)} {reason}",
        f"Content-Length: {len(body)}",
        f"Content-Type: {content_type}",
        "Connection: close",
        "\r\n",
    ]
    return ("\r\n".join(headers)).encode("latin-1", errors="strict") + body


def _make_ws_frame(*, payload: bytes, opcode: int) -> bytes:
    b1 = 0x80 | (opcode & 0x0F)  # FIN + opcode
    ln = len(payload)
    if ln < 126:
        header = bytes([b1, ln])
    elif ln <= 0xFFFF:
        header = bytes([b1, 126]) + ln.to_bytes(2, "big")
    else:
        header = bytes([b1, 127]) + ln.to_bytes(8, "big")
    return header + payload


async def _read_exact(reader: asyncio.StreamReader, n: int) -> bytes:
    data = await reader.readexactly(n)
    if len(data) != n:
        raise EOFError("short read")
    return data


async def _read_ws_frame(reader: asyncio.StreamReader) -> tuple[int, bytes]:
    head = await _read_exact(reader, 2)
    b1, b2 = head[0], head[1]
    fin = (b1 & 0x80) != 0
    opcode = b1 & 0x0F
    masked = (b2 & 0x80) != 0
    ln = b2 & 0x7F
    if not fin:
        raise ValueError("fragmented frames not supported")
    if ln == 126:
        ln = int.from_bytes(await _read_exact(reader, 2), "big")
    elif ln == 127:
        ln = int.from_bytes(await _read_exact(reader, 8), "big")
    mask = await _read_exact(reader, 4) if masked else b""
    payload = await _read_exact(reader, ln) if ln else b""
    if masked:
        payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    return opcode, payload


@dataclass(slots=True)
class _BufferedTask:
    priority: int
    seq: int
    task_id: str
    instruction: str
    target_repository: str | None
    enqueued_utc: str


@dataclass(slots=True)
class InMemoryScheduler:
    """Buffers excess triggers; flushes to `.platform_queue/next_task.json` one at a time."""

    poll_interval_s: float = 0.05
    stale_lock_s: float = 15 * 60.0

    _mu: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)
    _seq: int = field(default=0, init=False)
    _heap: list[tuple[int, int, _BufferedTask]] = field(default_factory=list, init=False)
    _flush_task: asyncio.Task[None] | None = field(default=None, init=False)
    _last_flush_error: str | None = field(default=None, init=False)

    async def start(self) -> None:
        ensure_runtime_directories()
        if self._flush_task is not None:
            return
        self._flush_task = asyncio.create_task(self._flush_loop(), name="gateway:scheduler:flush")

    async def stop(self) -> None:
        if self._flush_task is None:
            return
        self._flush_task.cancel()
        try:
            await self._flush_task
        except asyncio.CancelledError:
            pass
        self._flush_task = None

    async def enqueue(
        self,
        *,
        instruction: str,
        priority: int = 0,
        task_id: str | None = None,
        target_repository: str | None = None,
    ) -> str:
        if task_id is None:
            task_id = str(uuid.uuid4())
        task = _BufferedTask(
            priority=int(priority),
            seq=0,
            task_id=str(task_id),
            instruction=str(instruction),
            target_repository=str(target_repository) if isinstance(target_repository, str) and target_repository else None,
            enqueued_utc=_utc_ts(),
        )
        async with self._mu:
            self._seq += 1
            task.seq = self._seq
            # Higher priority first (min-heap).
            key = (-int(task.priority), int(task.seq), task)
            import heapq

            heapq.heappush(self._heap, key)
        return task.task_id

    async def snapshot(self) -> dict[str, Any]:
        lock_age_s = self._lock_age_s()
        lock_stale = lock_age_s is not None and lock_age_s > float(self.stale_lock_s)
        async with self._mu:
            buffered = len(self._heap)
            last_error = self._last_flush_error
        state = "Idle"
        if lock_stale:
            state = "Error-Locked"
        elif PLATFORM_LOCK_FILE.exists() or PLATFORM_TASK_FILE.exists():
            state = "Processing"
        return {
            "ts_utc": _utc_ts(),
            "state": state,
            "stale_lock_threshold_s": float(self.stale_lock_s),
            "buffered": buffered,
            "disk_task_present": PLATFORM_TASK_FILE.exists(),
            "processing_lock_present": PLATFORM_LOCK_FILE.exists(),
            "processing_lock_age_s": _readable_duration_s(lock_age_s),
            "processing_lock_details": _read_processing_lock_details(),
            "last_flush_error": last_error,
            "resources": _system_memory_metrics(),
        }

    def _lock_age_s(self) -> float | None:
        try:
            st = PLATFORM_LOCK_FILE.stat()
        except OSError:
            return None
        return time.time() - float(st.st_mtime)

    async def _flush_loop(self) -> None:
        import heapq

        while True:
            await asyncio.sleep(float(self.poll_interval_s))
            if PLATFORM_TASK_FILE.exists() or PLATFORM_LOCK_FILE.exists():
                continue

            async with self._mu:
                if not self._heap:
                    continue
                _neg_pri, _seq, task = heapq.heappop(self._heap)

            try:
                ensure_runtime_directories()
                self._write_new_task_file(task)
                self._last_flush_error = None
            except FileExistsError:
                # Another writer won the race; re-queue and retry later.
                async with self._mu:
                    heapq.heappush(self._heap, (-int(task.priority), int(task.seq), task))
            except Exception as exc:
                self._last_flush_error = str(exc)
                # Re-queue (don't drop tasks on transient fs errors).
                async with self._mu:
                    heapq.heappush(self._heap, (-int(task.priority), int(task.seq), task))

    def _write_new_task_file(self, task: _BufferedTask) -> None:
        payload: dict[str, Any] = {
            "task_id": task.task_id,
            "instruction": task.instruction,
            "enqueued_utc": task.enqueued_utc,
        }
        if task.target_repository:
            payload["target_repository"] = task.target_repository
        data = _json_bytes(payload)
        PLATFORM_TASK_FILE.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(str(PLATFORM_TASK_FILE), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
        except Exception:
            try:
                os.close(fd)
            except Exception:
                pass
            try:
                PLATFORM_TASK_FILE.unlink(missing_ok=True)
            except Exception:
                pass
            raise


@dataclass(slots=True)
class EventGateway:
    host: str = "127.0.0.1"
    port: int = 8080
    scheduler: InMemoryScheduler = field(default_factory=InMemoryScheduler)

    _server: asyncio.base_events.Server | None = field(default=None, init=False)

    async def start(self) -> None:
        await self.scheduler.start()
        if self._server is not None:
            return
        self._server = await asyncio.start_server(self._handle_conn, host=self.host, port=int(self.port))

    async def stop(self) -> None:
        await self.scheduler.stop()
        if self._server is None:
            return
        self._server.close()
        await self._server.wait_closed()
        self._server = None

    async def serve_forever(self) -> None:
        await self.start()
        assert self._server is not None
        await self._server.serve_forever()

    async def _handle_conn(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            lines = await _read_http_headers(reader)
            method, path, headers = _parse_headers(lines)
        except Exception:
            writer.close()
            return

        # WebSocket upgrade
        if path == "/ws/events" and headers.get("upgrade", "").lower() == "websocket":
            await self._handle_ws(method=method, headers=headers, reader=reader, writer=writer)
            return

        try:
            if path == "/health" and method == "GET":
                snapshot = await self.scheduler.snapshot()
                try:
                    snapshot["workspace"] = workspace_dir_health()
                except Exception as exc:
                    snapshot["workspace"] = {"error": str(exc)}
                snapshot["consensus"] = _consensus_metrics()
                semantic = _semantic_memory_metrics()
                snapshot["semantic_memory"] = semantic
                # Provide flat keys for quick dashboards (e.g. ConceptSHOP_memories_count).
                snapshot.update(semantic.get("flat_counts") or {})
                body = _json_bytes(snapshot)
                writer.write(_http_response(200, body))
                await writer.drain()
                writer.close()
                return

            if path == "/api/v1/trigger" and method == "POST":
                try:
                    content_length = int(headers.get("content-length", "0"))
                except Exception:
                    content_length = 0
                if content_length <= 0 or content_length > 512 * 1024:
                    writer.write(_http_response(400, _json_bytes({"error": "invalid content-length"})))
                    await writer.drain()
                    writer.close()
                    return

                raw = await reader.readexactly(content_length)
                try:
                    instruction, priority, target_repository = _parse_instruction_payload(raw)
                except Exception as exc:
                    writer.write(_http_response(400, _json_bytes({"error": str(exc)})))
                    await writer.drain()
                    writer.close()
                    return

                try:
                    priority = int(headers.get("x-priority", priority))
                except Exception:
                    pass

                task_id = await self.scheduler.enqueue(
                    instruction=instruction,
                    priority=priority,
                    target_repository=target_repository,
                )
                writer.write(_http_response(202, _json_bytes({"ok": True, "task_id": task_id})))
                await writer.drain()
                writer.close()
                return

            if path in ("/api/v1/trigger", "/health") and method not in ("GET", "POST"):
                writer.write(_http_response(405, _json_bytes({"error": "method not allowed"})))
                await writer.drain()
                writer.close()
                return

            writer.write(_http_response(404, _json_bytes({"error": "not found"})))
            await writer.drain()
        except Exception:
            try:
                writer.write(_http_response(500, _json_bytes({"error": "internal error"})))
                await writer.drain()
            except Exception:
                pass
        finally:
            try:
                writer.close()
            except Exception:
                pass

    async def _handle_ws(
        self,
        *,
        method: str,
        headers: dict[str, str],
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        if method != "GET":
            writer.write(_http_response(405, _json_bytes({"error": "method not allowed"})))
            await writer.drain()
            writer.close()
            return

        key = headers.get("sec-websocket-key")
        if not key:
            writer.write(_http_response(400, _json_bytes({"error": "missing sec-websocket-key"})))
            await writer.drain()
            writer.close()
            return

        accept = _ws_accept_value(key)
        resp = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept}\r\n"
            "\r\n"
        )
        writer.write(resp.encode("latin-1", errors="strict"))
        await writer.drain()

        while True:
            try:
                opcode, payload = await _read_ws_frame(reader)
            except asyncio.IncompleteReadError:
                return
            except Exception:
                return

            if opcode == 0x8:  # close
                try:
                    writer.write(_make_ws_frame(payload=b"", opcode=0x8))
                    await writer.drain()
                except Exception:
                    pass
                return

            if opcode == 0x9:  # ping
                try:
                    writer.write(_make_ws_frame(payload=payload, opcode=0xA))
                    await writer.drain()
                except Exception:
                    return
                continue

            if opcode != 0x1:
                continue

            try:
                instruction, priority, target_repository = _parse_instruction_payload(payload)
            except Exception:
                # Policy: immediately close on invalid payload to protect the core loop.
                try:
                    writer.write(_make_ws_frame(payload=b"", opcode=0x8))
                    await writer.drain()
                except Exception:
                    pass
                return

            task_id = await self.scheduler.enqueue(
                instruction=instruction,
                priority=priority,
                target_repository=target_repository,
            )
            try:
                writer.write(_make_ws_frame(payload=_json_bytes({"ok": True, "task_id": task_id}), opcode=0x1))
                await writer.drain()
            except Exception:
                return


async def _main() -> None:
    host = os.environ.get("GATEWAY_HOST", "127.0.0.1")
    port = int(os.environ.get("GATEWAY_PORT", "8080"))
    gateway = EventGateway(host=host, port=port)
    await gateway.serve_forever()


if __name__ == "__main__":
    asyncio.run(_main())
