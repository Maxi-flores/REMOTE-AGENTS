"""Async MCP bridge over WebSockets (stdlib-only, Python 3.10+).

This module exposes a minimal Model Context Protocol-compatible surface:
  - JSON-RPC `tools/list` + `tools/call`
  - JSON-RPC notifications for rollup + consensus events

It is intentionally dependency-free: a small RFC6455 subset is implemented on
top of asyncio streams (text frames only; no fragmentation).
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping


_WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


def _canonical_json(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _utc_ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _now_ms() -> float:
    return time.monotonic() * 1000.0


class _WSProtocolError(RuntimeError):
    pass


def _ws_accept_value(key: str) -> str:
    raw = (key + _WS_GUID).encode("ascii", errors="strict")
    digest = hashlib.sha1(raw).digest()
    return base64.b64encode(digest).decode("ascii")


async def _read_http_headers(reader: asyncio.StreamReader, *, limit: int = 64 * 1024) -> list[str]:
    try:
        raw = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout=5.0)
    except Exception as exc:  # pragma: no cover - network timing dependent
        raise _WSProtocolError("handshake timeout") from exc
    if len(raw) > limit:
        raise _WSProtocolError("handshake header too large")
    text = raw.decode("latin-1", errors="replace")
    return [line for line in text.split("\r\n") if line]


def _parse_headers(lines: list[str]) -> tuple[str, dict[str, str]]:
    if not lines:
        raise _WSProtocolError("empty handshake")
    request = lines[0]
    headers: dict[str, str] = {}
    for line in lines[1:]:
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        headers[k.strip().lower()] = v.strip()
    return request, headers


def _make_ws_frame(*, payload: bytes, opcode: int) -> bytes:
    if opcode not in (0x1, 0x2, 0x8, 0x9, 0xA):
        raise ValueError("unsupported opcode")
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
        raise _WSProtocolError("short read")
    return data


async def _read_ws_frame(reader: asyncio.StreamReader) -> tuple[int, bytes]:
    head = await _read_exact(reader, 2)
    b1, b2 = head[0], head[1]
    fin = (b1 & 0x80) != 0
    opcode = b1 & 0x0F
    masked = (b2 & 0x80) != 0
    ln = b2 & 0x7F
    if not fin:
        raise _WSProtocolError("fragmented frames not supported")
    if ln == 126:
        ln = int.from_bytes(await _read_exact(reader, 2), "big")
    elif ln == 127:
        ln = int.from_bytes(await _read_exact(reader, 8), "big")
    if masked:
        mask = await _read_exact(reader, 4)
    else:
        mask = b""
    payload = await _read_exact(reader, ln) if ln else b""
    if masked:
        payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    return opcode, payload


@dataclass(slots=True, eq=False)
class _WSConn:
    reader: asyncio.StreamReader
    writer: asyncio.StreamWriter
    send_mu: asyncio.Lock = field(default_factory=asyncio.Lock)
    closed: bool = False

    async def send_text(self, text: str) -> None:
        if self.closed:
            return
        data = text.encode("utf-8", errors="strict")
        frame = _make_ws_frame(payload=data, opcode=0x1)
        async with self.send_mu:
            try:
                self.writer.write(frame)
                await self.writer.drain()
            except Exception:
                self.closed = True

    async def send_jsonrpc(self, obj: Mapping[str, Any]) -> None:
        await self.send_text(_canonical_json(dict(obj)))

    async def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        try:
            self.writer.write(_make_ws_frame(payload=b"", opcode=0x8))
            await self.writer.drain()
        except Exception:
            pass
        try:
            self.writer.close()
        except Exception:
            pass


@dataclass(slots=True)
class _TailState:
    path: Path
    node_id: str
    kind: str  # "ledger" | "orphaned"
    pos: int = 0
    carry: bytes = b""


ToolHandler = Callable[[Mapping[str, Any]], Any]


@dataclass(slots=True)
class MCPBridge:
    """Non-blocking WebSocket bridge that streams ledger state to a 3D canvas."""

    host: str = "127.0.0.1"
    port: int = 8765
    poll_interval_s: float = 0.02

    _server: asyncio.base_events.Server | None = field(init=False, default=None)
    _clients_mu: asyncio.Lock = field(init=False, default_factory=asyncio.Lock)
    _clients: set[_WSConn] = field(init=False, default_factory=set)
    _tail_mu: asyncio.Lock = field(init=False, default_factory=asyncio.Lock)
    _tails: list[_TailState] = field(init=False, default_factory=list)
    _tail_task: asyncio.Task[None] | None = field(init=False, default=None)
    _tools: dict[str, ToolHandler] = field(init=False, default_factory=dict)

    def register_tool(self, name: str, handler: ToolHandler) -> None:
        self._tools[str(name)] = handler

    def register_consensus_logs(self, *, node_id: str, log_dir: Path) -> None:
        log_dir = log_dir.resolve()
        ledger = (log_dir / "PROOFS_LEDGER.jsonl").resolve()
        orphaned = (log_dir / "ORPHANED_FORKS.jsonl").resolve()
        self._tails.append(_TailState(path=ledger, node_id=str(node_id), kind="ledger"))
        self._tails.append(_TailState(path=orphaned, node_id=str(node_id), kind="orphaned"))

    async def start(self) -> None:
        if self._server is not None:
            return
        self._server = await asyncio.start_server(self._handle_client, host=self.host, port=int(self.port))
        self._tail_task = asyncio.create_task(self._tail_loop(), name="mcp-bridge:tail")

    async def stop(self) -> None:
        if self._tail_task is not None:
            self._tail_task.cancel()
            try:
                await self._tail_task
            except asyncio.CancelledError:
                pass
        self._tail_task = None

        async with self._clients_mu:
            clients = list(self._clients)
            self._clients.clear()
        await asyncio.gather(*(c.close() for c in clients), return_exceptions=True)

        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
        self._server = None

    async def notify_event(self, params: Mapping[str, Any]) -> None:
        """Broadcast a JSON-RPC notification to all connected clients."""
        msg = {"jsonrpc": "2.0", "method": "telemetry/event", "params": dict(params)}
        async with self._clients_mu:
            clients = list(self._clients)
        await asyncio.gather(*(c.send_jsonrpc(msg) for c in clients), return_exceptions=True)

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        conn = _WSConn(reader=reader, writer=writer)
        try:
            lines = await _read_http_headers(reader)
            _req, headers = _parse_headers(lines)
            key = headers.get("sec-websocket-key")
            if not key:
                raise _WSProtocolError("missing sec-websocket-key")
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
        except Exception:
            try:
                writer.close()
            except Exception:
                pass
            return

        async with self._clients_mu:
            self._clients.add(conn)

        try:
            await self._client_loop(conn)
        finally:
            async with self._clients_mu:
                self._clients.discard(conn)
            await conn.close()

    async def _client_loop(self, conn: _WSConn) -> None:
        while not conn.closed:
            try:
                opcode, payload = await _read_ws_frame(conn.reader)
            except asyncio.IncompleteReadError:
                return
            except Exception:
                return

            if opcode == 0x8:  # close
                return
            if opcode == 0x9:  # ping
                try:
                    conn.writer.write(_make_ws_frame(payload=payload, opcode=0xA))
                    await conn.writer.drain()
                except Exception:
                    return
                continue
            if opcode != 0x1:
                continue

            try:
                text = payload.decode("utf-8", errors="strict")
            except Exception:
                continue

            try:
                obj = json.loads(text)
            except Exception:
                continue
            if not isinstance(obj, dict):
                continue
            await self._handle_jsonrpc(conn, obj)

    async def _handle_jsonrpc(self, conn: _WSConn, msg: Mapping[str, Any]) -> None:
        method = msg.get("method")
        msg_id = msg.get("id")

        if method == "tools/list":
            tools = [
                {
                    "name": name,
                    "description": "runtime switch",
                    "inputSchema": {"type": "object"},
                }
                for name in sorted(self._tools.keys())
            ]
            await conn.send_jsonrpc({"jsonrpc": "2.0", "id": msg_id, "result": {"tools": tools}})
            return

        if method != "tools/call":
            if msg_id is not None:
                await conn.send_jsonrpc(
                    {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": "method not found"}}
                )
            return

        params = msg.get("params")
        if not isinstance(params, dict):
            await conn.send_jsonrpc({"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32602, "message": "bad params"}})
            return
        name = params.get("name")
        if not isinstance(name, str) or not name:
            await conn.send_jsonrpc({"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32602, "message": "tool name missing"}})
            return
        handler = self._tools.get(name)
        if handler is None:
            await conn.send_jsonrpc({"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": "tool not found"}})
            return
        args = params.get("arguments")
        if args is None:
            args = {}
        if not isinstance(args, dict):
            await conn.send_jsonrpc({"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32602, "message": "arguments must be object"}})
            return

        try:
            res = handler(args)
            if asyncio.iscoroutine(res):
                res = await res
        except Exception as exc:
            await conn.send_jsonrpc(
                {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32000, "message": str(exc)}}
            )
            return

        await conn.send_jsonrpc({"jsonrpc": "2.0", "id": msg_id, "result": {"content": [{"type": "json", "json": res}]}})

    async def _tail_loop(self) -> None:
        while True:
            await asyncio.sleep(float(self.poll_interval_s))
            async with self._tail_mu:
                tails = list(self._tails)
            for st in tails:
                try:
                    await self._tail_once(st)
                except Exception:
                    continue

    async def _tail_once(self, st: _TailState) -> None:
        try:
            size = st.path.stat().st_size
        except OSError:
            return
        if size < st.pos:
            st.pos = 0
            st.carry = b""
        if size == st.pos:
            return
        try:
            with st.path.open("rb") as f:
                f.seek(st.pos)
                data = f.read()
        except OSError:
            return
        st.pos += len(data)
        if not data:
            return
        blob = st.carry + data
        parts = blob.split(b"\n")
        st.carry = parts[-1]
        for raw in parts[:-1]:
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw.decode("utf-8", errors="replace"))
            except Exception:
                continue
            if not isinstance(obj, dict):
                continue
            if st.kind == "ledger":
                await self._emit_ledger_block(st.node_id, obj)
            else:
                await self._emit_orphaned(st.node_id, obj)

    async def _emit_ledger_block(self, node_id: str, blk: Mapping[str, Any]) -> None:
        payload = blk.get("payload")
        event: dict[str, Any] = {
            "ts_utc": _utc_ts(),
            "node_id": node_id,
            "kind": "LEDGER_BLOCK",
            "index": blk.get("index"),
            "hash": blk.get("hash"),
            "prev_hash": blk.get("prev_hash"),
            "execution_token": blk.get("execution_token"),
        }
        if isinstance(payload, dict) and payload.get("kind") == "ROLLUP_BLOCK":
            event["rollup"] = {
                "batch_id": payload.get("batch_id"),
                "seq_start": payload.get("seq_start"),
                "seq_end": payload.get("seq_end"),
                "tx_count": payload.get("tx_count"),
                "merkle_root": payload.get("merkle_root"),
                "correlation_mask": payload.get("correlation_mask"),
                "execution_token_hash": payload.get("execution_token_hash"),
                "target_ledger_root": payload.get("target_ledger_root"),
                "algo": payload.get("algo"),
            }
        await self.notify_event(event)

    async def _emit_orphaned(self, node_id: str, rec: Mapping[str, Any]) -> None:
        kind = rec.get("kind")
        details = rec.get("details") if isinstance(rec.get("details"), dict) else {}
        event: dict[str, Any] = {
            "ts_utc": _utc_ts(),
            "node_id": node_id,
            "kind": kind,
            "peer_id": rec.get("peer_id"),
            "details": dict(details),
        }
        if kind == "FRAUD_PROOF_QUARANTINE":
            payload = details.get("payload") if isinstance(details.get("payload"), dict) else {}
            if isinstance(payload, dict) and isinstance(payload.get("correlation_mask"), str):
                event["correlation_mask"] = payload.get("correlation_mask")
        await self.notify_event(event)


def build_default_tools(
    *,
    rollup_engines: Mapping[str, Any] | None = None,
    consensus_nodes: Mapping[str, Any] | None = None,
    cache_evictor: Callable[[], Any] | None = None,
) -> dict[str, ToolHandler]:
    """Helper for wiring common dashboard switches to runtime objects."""

    engines = dict(rollup_engines or {})
    nodes = dict(consensus_nodes or {})

    def _batch_ceiling(args: Mapping[str, Any]) -> Mapping[str, Any]:
        size = args.get("batch_size", args.get("value", args.get("ceiling")))
        if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
            raise ValueError("batch_size must be a positive integer")
        updated: list[str] = []
        for name, eng in engines.items():
            if hasattr(eng, "set_batch_size"):
                eng.set_batch_size(int(size))
                updated.append(str(name))
        return {"ok": True, "batch_size": int(size), "updated": updated}

    async def _quarantine_flush(args: Mapping[str, Any]) -> Mapping[str, Any]:
        target = args.get("node_id")
        flushed: list[str] = []
        for name, node in nodes.items():
            if target is not None and str(name) != str(target):
                continue
            if hasattr(node, "flush_quarantine"):
                res = node.flush_quarantine()
                if asyncio.iscoroutine(res):
                    await res
                flushed.append(str(name))
        return {"ok": True, "flushed": flushed}

    def _cache_evict(_args: Mapping[str, Any]) -> Mapping[str, Any]:
        if cache_evictor is None:
            raise ValueError("cache eviction not configured")
        res = cache_evictor()
        if asyncio.iscoroutine(res):
            raise ValueError("cache evictor must be sync")
        return {"ok": True}

    return {
        "batch_ceiling": _batch_ceiling,
        "quarantine_flush": _quarantine_flush,
        "cache_evict": _cache_evict,
    }
