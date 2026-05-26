import asyncio
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
import time

from core.consensus_node import BFTConsensusNode, pick_free_port


def _build_malicious_block(*, index: int, execution_token: str) -> dict[str, object]:
    # A syntactically valid block that intentionally violates prev_hash continuity.
    import hashlib

    def _canonical(obj: object) -> str:
        return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    prev_hash = "f" * 64
    header = {
        "index": index,
        "ts_utc": "1970-01-01T00:00:00Z",
        "execution_token": execution_token,
        "prev_hash": prev_hash,
        "payload": {"kind": "TX_COMMIT", "malicious": True},
    }
    h = hashlib.sha256(_canonical(header).encode("utf-8", errors="surrogatepass")).hexdigest()
    header["hash"] = h
    # Signature is non-secret FNV-1a over canonical JSON, matching core.hashutil.fnv1a_32 format.
    from core.hashutil import fnv1a_32

    header["signature"] = fnv1a_32(_canonical(header))
    return dict(header)


class TestBFTConsensusRig(unittest.IsolatedAsyncioTestCase):
    async def test_network_jitter_partition_and_quarantine(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        execution_token = "c" * 64

        ports = [pick_free_port() for _ in range(4)]
        node_ids = ["node-1", "node-2", "node-3", "node-4"]

        with TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            topo_path = tmp_root / "cluster_topology.json"
            topo = {
                "cluster_id": "TEST-CLUSTER",
                "nodes": [{"id": nid, "host": "127.0.0.1", "port": p} for nid, p in zip(node_ids, ports)],
            }
            topo_path.write_text(json.dumps(topo), encoding="utf-8")

            nodes: dict[str, BFTConsensusNode] = {}
            for nid in node_ids:
                log_dir = tmp_root / nid / "logs"
                nodes[nid] = BFTConsensusNode(
                    node_id=nid,
                    repo_root=repo_root,
                    log_dir=log_dir,
                    topology_path=topo_path,
                    execution_token=execution_token,
                    proposal_grace_ms=50,
                    reconnect_interval_ms=75,
                    jitter_ms=15,
                    drop_rate=0.05,
                    rng_seed=1337,
                )

            async def _start_all() -> None:
                await asyncio.gather(*(n.start() for n in nodes.values()))
                await asyncio.sleep(0.35)

            async def _wait_for_peer_links(*, src: str, peers: set[str], timeout_s: float = 2.0) -> None:
                deadline = time.monotonic() + timeout_s
                while time.monotonic() < deadline:
                    linked = set(nodes[src]._peers.keys())  # test-only introspection
                    if peers.issubset(linked):
                        return
                    await asyncio.sleep(0.05)
                self.fail(f"Timed out waiting for {src} to link peers={sorted(peers)}; have={sorted(linked)}")

            async def _stop_all() -> None:
                await asyncio.gather(*(n.stop() for n in nodes.values()), return_exceptions=True)

            try:
                await _start_all()
                await _wait_for_peer_links(src="node-4", peers={"node-1", "node-2", "node-3"})

                # Trigger a byzantine guard event: node-4 sends a syntactically valid block with a bad prev_hash.
                bad_block = _build_malicious_block(index=0, execution_token=execution_token)
                await asyncio.gather(
                    nodes["node-4"]._send_to_peer("node-1", {"type": "PROPOSE_BLOCK", "from": "node-4", "block": bad_block}),
                    nodes["node-4"]._send_to_peer("node-2", {"type": "PROPOSE_BLOCK", "from": "node-4", "block": bad_block}),
                    nodes["node-4"]._send_to_peer("node-3", {"type": "PROPOSE_BLOCK", "from": "node-4", "block": bad_block}),
                )
                await asyncio.sleep(0.2)

                # Concurrently submit conflicting payloads from the non-faulty nodes.
                committed0 = await asyncio.gather(
                    nodes["node-1"].submit_payload({"kind": "TX_COMMIT", "src": "node-1", "i": 0}),
                    nodes["node-2"].submit_payload({"kind": "TX_COMMIT", "src": "node-2", "i": 0}),
                    nodes["node-3"].submit_payload({"kind": "TX_COMMIT", "src": "node-3", "i": 0}),
                )
                self.assertTrue(all(isinstance(x, dict) for x in committed0))

                # Simulate a partition isolating node-3.
                nodes["node-1"].set_partition({"node-3"})
                nodes["node-2"].set_partition({"node-3"})
                nodes["node-3"].set_partition({"node-1", "node-2"})
                await asyncio.sleep(0.1)

                pending = [
                    asyncio.create_task(nodes["node-1"].submit_payload({"kind": "TX_COMMIT", "src": "node-1", "i": 1})),
                    asyncio.create_task(nodes["node-2"].submit_payload({"kind": "TX_COMMIT", "src": "node-2", "i": 1})),
                    asyncio.create_task(nodes["node-3"].submit_payload({"kind": "TX_COMMIT", "src": "node-3", "i": 1})),
                ]

                # While partitioned, consensus should not be able to commit (quorum=3) even under jitter.
                await asyncio.sleep(0.35)
                for nid in ("node-1", "node-2", "node-3"):
                    ledger = nodes[nid].ledger_path
                    self.assertTrue(ledger.exists())
                    lines = ledger.read_text(encoding="utf-8", errors="replace").splitlines()
                    self.assertEqual(len(lines), 1)

                # Heal the partition.
                nodes["node-1"].set_partition(set())
                nodes["node-2"].set_partition(set())
                nodes["node-3"].set_partition(set())

                committed1 = await asyncio.gather(*pending)
                self.assertTrue(all(isinstance(x, dict) for x in committed1))

                # Append a terminal reconciliation marker via the same consensus path.
                await asyncio.gather(
                    nodes["node-1"].submit_payload({"kind": "CONSENSUS_RECONCILIATION_COMPLETE", "reason": "partition_healed"}),
                    nodes["node-2"].submit_payload({"kind": "CONSENSUS_RECONCILIATION_COMPLETE", "reason": "partition_healed"}),
                    nodes["node-3"].submit_payload({"kind": "CONSENSUS_RECONCILIATION_COMPLETE", "reason": "partition_healed"}),
                )

                # Final ledgers must match exactly across non-faulty nodes (byte-for-byte).
                ledger_bytes = [nodes[nid].ledger_path.read_bytes() for nid in ("node-1", "node-2", "node-3")]
                self.assertEqual(ledger_bytes[0], ledger_bytes[1])
                self.assertEqual(ledger_bytes[1], ledger_bytes[2])

                last = json.loads(ledger_bytes[0].decode("utf-8").strip().splitlines()[-1])
                self.assertIsInstance(last, dict)
                payload = last.get("payload")
                self.assertIsInstance(payload, dict)
                self.assertEqual(payload.get("kind"), "CONSENSUS_RECONCILIATION_COMPLETE")

                # Discarded proposals + quarantine events must be persisted to ORPHANED_FORKS.jsonl.
                orphaned_text = nodes["node-1"].orphaned_path.read_text(encoding="utf-8", errors="replace")
                self.assertIn('"kind":"QUARANTINED"', orphaned_text)
                self.assertIn('"kind":"ORPHANED_PROPOSAL_NOT_SELECTED"', orphaned_text)
            finally:
                await _stop_all()


if __name__ == "__main__":
    unittest.main(verbosity=2)
