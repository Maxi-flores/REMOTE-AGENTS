import asyncio
import hashlib
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
import time

from core.consensus_node import BFTConsensusNode, pick_free_port
from core.hashutil import fnv1a_32
from core.rollup import (
    WorkspaceRollupEngine,
    compute_correlation_mask,
    compute_execution_token_hash,
    compute_target_ledger_root,
    merkle_root_from_transactions,
)


def _canonical(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _build_block(*, index: int, prev_hash: str, execution_token: str, payload: dict[str, object]) -> dict[str, object]:
    import hashlib

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


class TestRollupCompressionRig(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[1]
        self.execution_token = "d" * 64
        self.ports = [pick_free_port() for _ in range(4)]
        self.node_ids = ["node-1", "node-2", "node-3", "node-4"]

    async def _start_cluster(self) -> tuple[dict[str, BFTConsensusNode], Path, Path]:
        with TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            topo_path = tmp_root / "cluster_topology.json"
            topo = {
                "cluster_id": "ROLLUP-TEST-CLUSTER",
                "nodes": [{"id": nid, "host": "127.0.0.1", "port": p} for nid, p in zip(self.node_ids, self.ports)],
            }
            topo_path.write_text(json.dumps(topo), encoding="utf-8")

            nodes: dict[str, BFTConsensusNode] = {}
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

            async def _wait_for_peer_links(*, src: str, peers: set[str], timeout_s: float = 2.0) -> None:
                deadline = time.monotonic() + timeout_s
                while time.monotonic() < deadline:
                    linked = set(nodes[src]._peers.keys())  # test-only introspection
                    if peers.issubset(linked):
                        return
                    await asyncio.sleep(0.05)
                self.fail(f"Timed out waiting for {src} to link peers={sorted(peers)}; have={sorted(linked)}")

            async def _run() -> None:
                await asyncio.gather(*(n.start() for n in nodes.values()))
                await asyncio.sleep(0.25)
                await _wait_for_peer_links(src="node-1", peers={"node-2", "node-3", "node-4"})
                await _wait_for_peer_links(src="node-2", peers={"node-1", "node-3", "node-4"})

            async def _stop() -> None:
                await asyncio.gather(*(n.stop() for n in nodes.values()), return_exceptions=True)

            await _run()
            try:
                yield nodes, tmp_root, topo_path
            finally:
                await _stop()

    async def test_01_compression_ratio_single_ledger_block(self) -> None:
        async for nodes, tmp_root, _topo in self._start_cluster():
            engines = {nid: WorkspaceRollupEngine(log_dir=(tmp_root / nid / "logs"), batch_size=100) for nid in self.node_ids}

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

            # Rollup journal has 100 entries, but consensus ledger must have exactly 1 committed block.
            for nid in self.node_ids:
                journal_lines = engines[nid].journal_path.read_text(encoding="utf-8", errors="replace").splitlines()
                self.assertEqual(len(journal_lines), 100)
                ledger_lines = nodes[nid].ledger_path.read_text(encoding="utf-8", errors="replace").splitlines()
                self.assertEqual(len(ledger_lines), 1)

    async def test_02_verifiable_validation_byte_identical_ledgers(self) -> None:
        async for nodes, tmp_root, _topo in self._start_cluster():
            engines = {nid: WorkspaceRollupEngine(log_dir=(tmp_root / nid / "logs"), batch_size=100) for nid in self.node_ids}

            txs: list[dict[str, object]] = []
            for i in range(100):
                txs.append(
                    {
                        "correlation_id": f"cid-{i % 7}",
                        "event": "PIPELINE_TICK",
                        "wall_ms": float(i % 5) + 0.5,
                        "cpu_ms": float(i % 3) + 0.25,
                        "bytes_transferred": 512 + i,
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

            ledger_bytes = [nodes[nid].ledger_path.read_bytes() for nid in self.node_ids]
            self.assertEqual(ledger_bytes[0], ledger_bytes[1])
            self.assertEqual(ledger_bytes[1], ledger_bytes[2])
            self.assertEqual(ledger_bytes[2], ledger_bytes[3])

            blk = json.loads(ledger_bytes[0].decode("utf-8").strip().splitlines()[-1])
            self.assertIsInstance(blk, dict)
            payload = blk.get("payload")
            self.assertIsInstance(payload, dict)
            self.assertEqual(payload.get("kind"), "ROLLUP_BLOCK")
            self.assertEqual(payload.get("tx_count"), 100)

            expected_merkle = merkle_root_from_transactions(txs)
            expected_mask = compute_correlation_mask((str(t["correlation_id"]) for t in txs))
            total_wall = sum(float(t["wall_ms"]) for t in txs)
            total_cpu = sum(float(t["cpu_ms"]) for t in txs)
            total_bytes = sum(int(t["bytes_transferred"]) for t in txs)
            expected_token = compute_execution_token_hash(wall_ms=total_wall, cpu_ms=total_cpu, bytes_transferred=total_bytes)
            expected_target = compute_target_ledger_root(
                previous_ledger_root="0" * 64,
                merkle_root=str(payload["merkle_root"]),
                correlation_mask=str(payload["correlation_mask"]),
                execution_token_hash=str(payload["execution_token_hash"]),
                seq_start=int(payload["seq_start"]),
                seq_end=int(payload["seq_end"]),
                tx_count=int(payload["tx_count"]),
            )

            self.assertEqual(str(payload.get("previous_ledger_root")), "0" * 64)
            self.assertEqual(str(payload.get("merkle_root")), expected_merkle)
            self.assertEqual(str(payload.get("correlation_mask")), expected_mask)
            self.assertEqual(str(payload.get("execution_token_hash")), expected_token)
            self.assertEqual(str(payload.get("target_ledger_root")), expected_target)

    async def test_03_fraud_invalidation_quarantines_malicious_leader(self) -> None:
        async for nodes, tmp_root, _topo in self._start_cluster():
            engines = {nid: WorkspaceRollupEngine(log_dir=(tmp_root / nid / "logs"), batch_size=100) for nid in self.node_ids}

            # Mirror 100 deterministic transactions into every node journal (no consensus submission).
            txs: list[dict[str, object]] = []
            for i in range(100):
                txs.append(
                    {
                        "correlation_id": f"cid-{i % 5}",
                        "event": "CACHE_MISS",
                        "wall_ms": 2.0,
                        "cpu_ms": 1.0,
                        "bytes_transferred": 2048 + i,
                    }
                )
            for tx in txs:
                for nid in self.node_ids:
                    engines[nid].ingest_transaction(
                        correlation_id=str(tx["correlation_id"]),
                        event=str(tx["event"]),
                        wall_ms=float(tx["wall_ms"]),
                        cpu_ms=float(tx["cpu_ms"]),
                        bytes_transferred=int(tx["bytes_transferred"]),
                    )

            # Craft a syntactically valid rollup payload but corrupt the execution_token_hash.
            expected_merkle = merkle_root_from_transactions(txs)
            expected_mask = compute_correlation_mask((str(t["correlation_id"]) for t in txs))
            total_wall = sum(float(t["wall_ms"]) for t in txs)
            total_cpu = sum(float(t["cpu_ms"]) for t in txs)
            total_bytes = sum(int(t["bytes_transferred"]) for t in txs)
            expected_token = compute_execution_token_hash(wall_ms=total_wall, cpu_ms=total_cpu, bytes_transferred=total_bytes)
            corrupted_token = expected_token[:-1] + ("0" if expected_token[-1] != "0" else "1")
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
            await asyncio.sleep(0.2)

            for nid in ("node-2", "node-3", "node-4"):
                orphaned_text = nodes[nid].orphaned_path.read_text(encoding="utf-8", errors="replace")
                self.assertIn('"kind":"FRAUD_PROOF_QUARANTINE"', orphaned_text)
                self.assertIn('"peer_id":"node-1"', orphaned_text)
                self.assertIn("node-1", nodes[nid]._quarantined_peers)  # test-only introspection
                self.assertFalse(nodes[nid].ledger_path.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
