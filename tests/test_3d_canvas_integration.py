import asyncio
import base64
import hashlib
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
import time

from core.cache import WorkspaceCacheEngine
from core.consensus_node import BFTConsensusNode, pick_free_port
from core.hashutil import fnv1a_32
from core.mcp_bridge import MCPBridge, build_default_tools
from core.rollup import (
    WorkspaceRollupEngine,
    compute_correlation_mask,
    compute_execution_token_hash,
    compute_target_ledger_root,
    merkle_root_from_transactions,
)


_WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


def _canonical(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _ws_accept_value(key: str) -> str:
    digest = hashlib.sha1((key + _WS_GUID).encode("ascii", errors="strict")).digest()
    return base64.b64encode(digest).decode("ascii")


def _make_frame(*, payload: bytes, opcode: int, masked: bool) -> bytes:
    b1 = 0x80 | (opcode & 0x0F)
    ln = len(payload)
    if ln < 126:
        header = bytes([b1, (0x80 if masked else 0x00) | ln])
    elif ln <= 0xFFFF:
        header = bytes([b1, (0x80 if masked else 0x00) | 126]) + ln.to_bytes(2, "big")
    else:
        header = bytes([b1, (0x80 if masked else 0x00) | 127]) + ln.to_bytes(8, "big")
    if not masked:
        return header + payload
    mask = b"\x01\x02\x03\x04"
    masked_payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    return header + mask + masked_payload


async def _read_exact(reader: asyncio.StreamReader, n: int) -> bytes:
    data = await reader.readexactly(n)
    if len(data) != n:
        raise RuntimeError("short read")
    return data


async def _read_frame(reader: asyncio.StreamReader) -> tuple[int, bytes]:
    head = await _read_exact(reader, 2)
    b1, b2 = head[0], head[1]
    fin = (b1 & 0x80) != 0
    opcode = b1 & 0x0F
    masked = (b2 & 0x80) != 0
    ln = b2 & 0x7F
    if not fin:
        raise RuntimeError("fragmented frames not supported")
    if ln == 126:
        ln = int.from_bytes(await _read_exact(reader, 2), "big")
    elif ln == 127:
        ln = int.from_bytes(await _read_exact(reader, 8), "big")
    mask = await _read_exact(reader, 4) if masked else b""
    payload = await _read_exact(reader, ln) if ln else b""
    if masked:
        payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    return opcode, payload


def _build_block(*, index: int, prev_hash: str, execution_token: str, payload: dict[str, object]) -> dict[str, object]:
    header: dict[str, object] = {
        "index": int(index),
        "ts_utc": "1970-01-01T00:00:00Z",
        "execution_token": str(execution_token),
        "prev_hash": str(prev_hash),
        "payload": dict(payload),
    }
    h = hashlib.sha256(_canonical(header).encode("utf-8", errors="surrogatepass")).hexdigest()
    header["hash"] = h
    header["signature"] = fnv1a_32(_canonical(header))
    return dict(header)


class _WsJsonClient:
    def __init__(self, host: str, port: int) -> None:
        self._host = host
        self._port = port
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None

    async def connect(self) -> None:
        reader, writer = await asyncio.open_connection(host=self._host, port=self._port)
        key = base64.b64encode(b"test-key-3d").decode("ascii")
        req = (
            "GET / HTTP/1.1\r\n"
            f"Host: {self._host}:{self._port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "\r\n"
        )
        writer.write(req.encode("latin-1", errors="strict"))
        await writer.drain()

        raw = await reader.readuntil(b"\r\n\r\n")
        head = raw.decode("latin-1", errors="replace")
        self.assertIn("101 Switching Protocols", head)
        self.assertIn(_ws_accept_value(key), head)

        self._reader = reader
        self._writer = writer

    async def close(self) -> None:
        if self._writer is None:
            return
        try:
            self._writer.write(_make_frame(payload=b"", opcode=0x8, masked=True))
            await self._writer.drain()
        except Exception:
            pass
        try:
            self._writer.close()
        except Exception:
            pass
        self._reader = None
        self._writer = None

    async def send_json(self, obj: object) -> None:
        if self._writer is None:
            raise RuntimeError("not connected")
        data = _canonical(obj).encode("utf-8", errors="surrogatepass")
        self._writer.write(_make_frame(payload=data, opcode=0x1, masked=True))
        await self._writer.drain()

    async def recv_json(self) -> dict[str, object]:
        if self._reader is None:
            raise RuntimeError("not connected")
        while True:
            opcode, payload = await _read_frame(self._reader)
            if opcode == 0x8:
                raise RuntimeError("closed")
            if opcode != 0x1:
                continue
            obj = json.loads(payload.decode("utf-8", errors="replace"))
            if isinstance(obj, dict):
                return obj

    # unittest-style assertion helpers (no pytest)
    def assertIn(self, a: object, b: object) -> None:
        assert a in b  # noqa: S101 (unit test)


class Test3DCanvasIntegration(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[1]
        self.execution_token = "d" * 64
        self.ports = [pick_free_port() for _ in range(4)]
        self.node_ids = ["node-1", "node-2", "node-3", "node-4"]

    async def _start_cluster(self) -> tuple[dict[str, BFTConsensusNode], dict[str, WorkspaceRollupEngine], Path]:
        tmp = TemporaryDirectory()
        tmp_root = Path(tmp.name)
        topo_path = tmp_root / "cluster_topology.json"
        topo = {
            "cluster_id": "DASHBOARD-3D-TEST-CLUSTER",
            "nodes": [{"id": nid, "host": "127.0.0.1", "port": p} for nid, p in zip(self.node_ids, self.ports)],
        }
        topo_path.write_text(json.dumps(topo), encoding="utf-8")

        nodes: dict[str, BFTConsensusNode] = {}
        engines: dict[str, WorkspaceRollupEngine] = {}
        for nid in self.node_ids:
            log_dir = tmp_root / nid / "logs"
            nodes[nid] = BFTConsensusNode(
                node_id=nid,
                repo_root=self.repo_root,
                log_dir=log_dir,
                topology_path=topo_path,
                execution_token=self.execution_token,
                proposal_grace_ms=35,
                reconnect_interval_ms=50,
                jitter_ms=0,
                drop_rate=0.0,
                rng_seed=424242,
            )
            engines[nid] = WorkspaceRollupEngine(log_dir=log_dir, batch_size=100)

        async def _run() -> None:
            await asyncio.gather(*(n.start() for n in nodes.values()))
            await asyncio.sleep(0.3)

        async def _stop() -> None:
            await asyncio.gather(*(n.stop() for n in nodes.values()), return_exceptions=True)
            tmp.cleanup()

        await _run()
        self.addAsyncCleanup(_stop)
        return nodes, engines, tmp_root

    async def test_rollup_and_quarantine_stream_to_canvas(self) -> None:
        nodes, engines, tmp_root = await self._start_cluster()

        bridge_port = pick_free_port()
        cache = WorkspaceCacheEngine(repo_root=self.repo_root)
        bridge = MCPBridge(host="127.0.0.1", port=bridge_port, poll_interval_s=0.01)
        for nid in self.node_ids:
            bridge.register_consensus_logs(node_id=nid, log_dir=(tmp_root / nid / "logs"))
        for name, handler in build_default_tools(
            rollup_engines={"node-1": engines["node-1"]},
            consensus_nodes=nodes,
            cache_evictor=cache.evict_objects,
        ).items():
            bridge.register_tool(name, handler)

        await bridge.start()
        self.addAsyncCleanup(bridge.stop)

        ws = _WsJsonClient("127.0.0.1", bridge_port)
        await ws.connect()
        self.addAsyncCleanup(ws.close)

        # Validate tool wiring via the MCP `tools/call` shape.
        await ws.send_json(
            {
                "jsonrpc": "2.0",
                "id": "tool-1",
                "method": "tools/call",
                "params": {"name": "batch_ceiling", "arguments": {"batch_size": 50}},
            }
        )
        tool_resp = await ws.recv_json()
        self.assertEqual(tool_resp.get("id"), "tool-1")
        self.assertEqual(engines["node-1"].batch_size, 50)
        await ws.send_json(
            {
                "jsonrpc": "2.0",
                "id": "tool-2",
                "method": "tools/call",
                "params": {"name": "batch_ceiling", "arguments": {"batch_size": 100}},
            }
        )
        await ws.recv_json()
        self.assertEqual(engines["node-1"].batch_size, 100)

        # Flood 100 transactions through the rollup engine; the bridge must emit a synchronized rollup event.
        txs: list[dict[str, object]] = []
        for i in range(100):
            txs.append(
                {
                    "correlation_id": f"cid-{i % 11}",
                    "event": "CACHE_HIT",
                    "wall_ms": 1.0,
                    "cpu_ms": 0.25,
                    "bytes_transferred": 10 + i,
                }
            )

        async def _submit_one(tx: dict[str, object]) -> None:
            for nid in ("node-2", "node-3", "node-4"):
                engines[nid].ingest_transaction(
                    correlation_id=str(tx["correlation_id"]),
                    event=str(tx["event"]),
                    wall_ms=float(tx["wall_ms"]),
                    cpu_ms=float(tx["cpu_ms"]),
                    bytes_transferred=int(tx["bytes_transferred"]),
                )
            await engines["node-1"].submit_transaction(
                consensus_node=nodes["node-1"],
                correlation_id=str(tx["correlation_id"]),
                event=str(tx["event"]),
                wall_ms=float(tx["wall_ms"]),
                cpu_ms=float(tx["cpu_ms"]),
                bytes_transferred=int(tx["bytes_transferred"]),
            )

        await asyncio.gather(*(_submit_one(tx) for tx in txs))
        t0 = time.monotonic()

        expected_merkle = merkle_root_from_transactions(txs)
        expected_mask = compute_correlation_mask((str(t["correlation_id"]) for t in txs))

        async def _wait_for_rollup(timeout_s: float = 1.0) -> dict[str, object]:
            deadline = time.monotonic() + timeout_s
            while time.monotonic() < deadline:
                msg = await ws.recv_json()
                if msg.get("method") != "telemetry/event":
                    continue
                params = msg.get("params")
                if not isinstance(params, dict):
                    continue
                if params.get("kind") != "LEDGER_BLOCK":
                    continue
                rollup = params.get("rollup")
                if not isinstance(rollup, dict):
                    continue
                if rollup.get("tx_count") != 100:
                    continue
                return msg
            self.fail("Timed out waiting for rollup event")

        rollup_msg = await _wait_for_rollup()
        elapsed_ms = (time.monotonic() - t0) * 1000.0
        self.assertLess(elapsed_ms, 250.0, f"rollup event latency too high: {elapsed_ms:.1f}ms")

        params = rollup_msg["params"]
        self.assertIsInstance(params, dict)
        rollup = params["rollup"]
        self.assertIsInstance(rollup, dict)
        self.assertEqual(rollup.get("merkle_root"), expected_merkle)
        self.assertEqual(rollup.get("correlation_mask"), expected_mask)
        self.assertEqual(params.get("execution_token"), self.execution_token)

        # Now simulate a byzantine leader (node-1) sending an invalid rollup payload.
        for tx in txs:
            for nid in self.node_ids:
                engines[nid].ingest_transaction(
                    correlation_id=str(tx["correlation_id"]),
                    event="CACHE_MISS",
                    wall_ms=2.0,
                    cpu_ms=1.0,
                    bytes_transferred=int(tx["bytes_transferred"]),
                )

        total_wall = sum(float(t["wall_ms"]) for t in txs)
        total_cpu = sum(float(t["cpu_ms"]) for t in txs)
        total_bytes = sum(int(t["bytes_transferred"]) for t in txs)
        token = compute_execution_token_hash(wall_ms=total_wall, cpu_ms=total_cpu, bytes_transferred=total_bytes)
        corrupted_token = token[:-1] + ("0" if token[-1] != "0" else "1")
        target = compute_target_ledger_root(
            previous_ledger_root="0" * 64,
            merkle_root=expected_merkle,
            correlation_mask=expected_mask,
            execution_token_hash=corrupted_token,
            seq_start=1,
            seq_end=100,
            tx_count=100,
        )
        proof_material = _canonical(
            {
                "previous_ledger_root": "0" * 64,
                "target_ledger_root": target,
                "correlation_mask": expected_mask,
                "execution_token_hash": corrupted_token,
            }
        ).encode("utf-8", errors="surrogatepass")
        proof_hash = hashlib.sha256(proof_material).hexdigest()
        malicious_payload = {
            "kind": "ROLLUP_BLOCK",
            "batch_id": "malicious:1-100",
            "seq_start": 1,
            "seq_end": 100,
            "tx_count": 100,
            "previous_ledger_root": "0" * 64,
            "merkle_root": expected_merkle,
            "correlation_mask": expected_mask,
            "execution_token_hash": corrupted_token,
            "target_ledger_root": target,
            "zk_proof": {
                "previous_ledger_root": "0" * 64,
                "target_ledger_root": target,
                "correlation_mask": expected_mask,
                "execution_token_hash": corrupted_token,
                "proof_hash": proof_hash,
            },
            "algo": "sha256/merkle:v1",
        }

        bad_block = _build_block(index=0, prev_hash="0" * 64, execution_token=self.execution_token, payload=malicious_payload)
        await asyncio.gather(
            nodes["node-1"]._send_to_peer("node-2", {"type": "PROPOSE_BLOCK", "from": "node-1", "block": bad_block}),
            nodes["node-1"]._send_to_peer("node-3", {"type": "PROPOSE_BLOCK", "from": "node-1", "block": bad_block}),
            nodes["node-1"]._send_to_peer("node-4", {"type": "PROPOSE_BLOCK", "from": "node-1", "block": bad_block}),
        )

        async def _wait_for_quarantine(timeout_s: float = 1.0) -> dict[str, object]:
            deadline = time.monotonic() + timeout_s
            while time.monotonic() < deadline:
                msg = await ws.recv_json()
                if msg.get("method") != "telemetry/event":
                    continue
                params = msg.get("params")
                if not isinstance(params, dict):
                    continue
                if params.get("kind") != "FRAUD_PROOF_QUARANTINE":
                    continue
                if params.get("peer_id") != "node-1":
                    continue
                return msg
            self.fail("Timed out waiting for quarantine event")

        quarantine_msg = await _wait_for_quarantine()
        qparams = quarantine_msg["params"]
        self.assertIsInstance(qparams, dict)
        self.assertEqual(qparams.get("correlation_mask"), expected_mask)


if __name__ == "__main__":
    unittest.main(verbosity=2)
