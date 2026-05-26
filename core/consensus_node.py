"""Async TCP-based BFT state machine replication (stdlib-only, Python 3.10+).

The local fork resolver (`core/fork_resolver.py`) protects a single-node runtime
from concurrent writers. Once agent runners scale out across multiple remote
nodes, the ledger must be *ordered* across the network before blocks are written
to disk.

This module implements a minimal, deterministic, PBFT-inspired 3-phase protocol:
  1) Pre-Prepare: a rotating leader broadcasts a candidate ledger block
  2) Prepare: peers validate and broadcast PREPARE tokens
  3) Commit: on strict prepare quorum (2f+1 of 3f+1), peers broadcast COMMIT and
     append the block to `logs/PROOFS_LEDGER.jsonl`

Safety rules are intentionally strict: a peer that proposes an unexpected index
or prev_hash for the local ledger head is treated as byzantine (quarantined).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import random
import socket
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, MutableMapping, TypedDict, cast

from core.exceptions import ByzantineNodeException
from core.hashutil import fnv1a_32
from core.replay import ReadOnlyWorkspaceGuard


class _TopologyNode(TypedDict):
    id: str
    host: str
    port: int


class _ClusterTopology(TypedDict):
    cluster_id: str
    nodes: list[_TopologyNode]


class LedgerBlock(TypedDict):
    index: int
    ts_utc: str
    execution_token: str
    prev_hash: str
    payload: object
    hash: str
    signature: str


_GENESIS_PREV = "0" * 64


class _DropConnection(RuntimeError):
    """Internal control-flow: close a connection without quarantine."""


def _canonical_json(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _now_ts_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _looks_like_hash(value: str, *, n: int) -> bool:
    if not isinstance(value, str) or len(value) != n:
        return False
    for ch in value:
        if ch not in "0123456789abcdef":
            return False
    return True


def _compute_block_hash(block_without_hash_and_sig: Mapping[str, Any]) -> str:
    material = _canonical_json(block_without_hash_and_sig).encode("utf-8", errors="surrogatepass")
    return hashlib.sha256(material).hexdigest()


def _compute_block_signature(block_without_sig: Mapping[str, Any]) -> str:
    return fnv1a_32(_canonical_json(block_without_sig))


def _coerce_block(obj: object) -> LedgerBlock | None:
    if not isinstance(obj, dict):
        return None
    idx = obj.get("index")
    ts_utc = obj.get("ts_utc")
    token = obj.get("execution_token")
    prev_hash = obj.get("prev_hash")
    payload = obj.get("payload")
    h = obj.get("hash")
    sig = obj.get("signature")
    if not isinstance(idx, int) or isinstance(idx, bool):
        return None
    if not isinstance(ts_utc, str) or not ts_utc:
        return None
    if not isinstance(token, str) or not token:
        return None
    if not isinstance(prev_hash, str) or not _looks_like_hash(prev_hash, n=64):
        return None
    if not isinstance(h, str) or not _looks_like_hash(h, n=64):
        return None
    if not isinstance(sig, str) or not _looks_like_hash(sig, n=8):
        return None
    return cast(
        LedgerBlock,
        {
            "index": idx,
            "ts_utc": ts_utc,
            "execution_token": token,
            "prev_hash": prev_hash,
            "payload": payload,
            "hash": h,
            "signature": sig,
        },
    )


def _block_is_self_consistent(block: LedgerBlock) -> bool:
    header = {
        "index": block.get("index"),
        "ts_utc": block.get("ts_utc"),
        "execution_token": block.get("execution_token"),
        "prev_hash": block.get("prev_hash"),
        "payload": block.get("payload"),
    }
    want_hash = _compute_block_hash(cast(Mapping[str, Any], header))
    if block.get("hash") != want_hash:
        return False
    header_with_hash: MutableMapping[str, Any] = dict(header)
    header_with_hash["hash"] = want_hash
    want_sig = _compute_block_signature(cast(Mapping[str, Any], header_with_hash))
    return block.get("signature") == want_sig


def _hydrate_tail(ledger_path: Path) -> tuple[int, str]:
    """Best-effort tail hydration: returns (next_index, prev_hash)."""
    try:
        if not ledger_path.exists():
            return (0, _GENESIS_PREV)
        lines = ledger_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return (0, _GENESIS_PREV)
    for raw in reversed(lines):
        raw = raw.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except Exception:
            continue
        blk = _coerce_block(obj)
        if blk is None:
            continue
        idx = blk.get("index")
        h = blk.get("hash")
        if isinstance(idx, int) and isinstance(h, str) and _looks_like_hash(h, n=64):
            return (idx + 1, h)
    return (0, _GENESIS_PREV)


def _append_jsonl_atomic(path: Path, record: Mapping[str, Any]) -> None:
    line = _canonical_json(record)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
        f.flush()
        try:
            os.fsync(f.fileno())
        except OSError:
            pass


def _peer_addr(writer: asyncio.StreamWriter) -> str:
    info = writer.get_extra_info("peername")
    if isinstance(info, tuple) and info:
        return f"{info[0]}:{info[1]}"
    return "unknown"


@dataclass(frozen=True, slots=True)
class _ProposalCandidate:
    from_id: str
    payload: Mapping[str, Any]

    def stable_key(self) -> tuple[str, str]:
        digest = hashlib.sha256(_canonical_json({"from": self.from_id, "payload": self.payload}).encode("utf-8")).hexdigest()
        return (digest, self.from_id)


@dataclass(slots=True)
class _ConsensusHeight:
    index: int
    prev_hash: str
    proposal: LedgerBlock | None = None
    prepares: set[str] = field(default_factory=set)
    commits: set[str] = field(default_factory=set)
    committed: bool = False

    def proposal_hash(self) -> str | None:
        if self.proposal is None:
            return None
        return str(self.proposal.get("hash") or "")


@dataclass(slots=True)
class _PeerConn:
    writer: asyncio.StreamWriter
    is_outbound: bool
    peer_id: str | None = None
    send_mu: asyncio.Lock = field(default_factory=asyncio.Lock)
    quarantined: bool = False

    @property
    def addr(self) -> str:
        return _peer_addr(self.writer)


@dataclass(slots=True)
class BFTConsensusNode:
    """Async cluster peer participating in 3-phase block replication."""

    node_id: str
    repo_root: Path
    log_dir: Path
    topology_path: Path
    execution_token: str
    proposal_grace_ms: int = 75
    reconnect_interval_ms: int = 250
    jitter_ms: int = 0
    drop_rate: float = 0.0
    rng_seed: int | None = None

    _cluster_id: str = field(init=False, default="cluster")
    _nodes: list[_TopologyNode] = field(init=False, default_factory=list)
    _self_host: str = field(init=False, default="127.0.0.1")
    _self_port: int = field(init=False, default=0)
    _server: asyncio.base_events.Server | None = field(init=False, default=None)
    _closed: bool = field(init=False, default=False)
    _peers_mu: asyncio.Lock = field(init=False, default_factory=asyncio.Lock)
    _peers: dict[str, _PeerConn] = field(init=False, default_factory=dict)
    _reader_tasks: set[asyncio.Task[None]] = field(init=False, default_factory=set)
    _reconnector: asyncio.Task[None] | None = field(init=False, default=None)
    _partition_blocked_peers: set[str] = field(init=False, default_factory=set)
    _quarantined_peers: set[str] = field(init=False, default_factory=set)
    _orphaned_path: Path = field(init=False)
    _ledger_path: Path = field(init=False)
    _state_mu: asyncio.Lock = field(init=False, default_factory=asyncio.Lock)
    _height: _ConsensusHeight = field(init=False)
    _pending: dict[int, list[_ProposalCandidate]] = field(init=False, default_factory=dict)
    _propose_tasks: dict[int, asyncio.Task[None]] = field(init=False, default_factory=dict)
    _commit_waiters: dict[int, list[asyncio.Future[LedgerBlock]]] = field(init=False, default_factory=dict)
    _rng: random.Random = field(init=False)

    def __post_init__(self) -> None:
        self.repo_root = self.repo_root.resolve()
        self.log_dir = self.log_dir.resolve()
        self.topology_path = self.topology_path.resolve()
        self._ledger_path = (self.log_dir / "PROOFS_LEDGER.jsonl").resolve()
        self._orphaned_path = (self.log_dir / "ORPHANED_FORKS.jsonl").resolve()
        seed = self.rng_seed if self.rng_seed is not None else int.from_bytes(os.urandom(8), "big")
        self._rng = random.Random(seed)
        next_index, prev_hash = _hydrate_tail(self._ledger_path)
        self._height = _ConsensusHeight(index=next_index, prev_hash=prev_hash)

    @property
    def ledger_path(self) -> Path:
        return self._ledger_path

    @property
    def orphaned_path(self) -> Path:
        return self._orphaned_path

    def quarantine_peer(self, peer_id: str) -> None:
        """Prevent reconnects to a peer (used by tests and byzantine guardrails)."""
        self._quarantined_peers.add(peer_id)

    def set_partition(self, blocked_peers: Iterable[str]) -> None:
        """Simulate a network partition by blocking connections/messages to peers."""
        self._partition_blocked_peers = set(blocked_peers)

    def _peer_is_blocked(self, peer_id: str) -> bool:
        return peer_id in self._quarantined_peers or peer_id in self._partition_blocked_peers

    async def start(self) -> None:
        topo = self._load_topology(self.topology_path)
        self._cluster_id = topo["cluster_id"]
        self._nodes = topo["nodes"]
        me = next((n for n in self._nodes if n["id"] == self.node_id), None)
        if me is None:
            raise ValueError(f"node_id not found in topology: {self.node_id}")
        self._self_host = me["host"]
        self._self_port = int(me["port"])

        self._server = await asyncio.start_server(self._handle_inbound, host=self._self_host, port=self._self_port)
        self._closed = False
        self._reconnector = asyncio.create_task(self._reconnect_loop(), name=f"bft-reconnect:{self.node_id}")

    async def stop(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._reconnector is not None:
            self._reconnector.cancel()
            try:
                await self._reconnector
            except asyncio.CancelledError:
                pass
        async with self._peers_mu:
            peers = list(self._peers.items())
            self._peers.clear()
        for _, peer in peers:
            try:
                peer.writer.close()
            except Exception:
                pass
        for task in list(self._reader_tasks):
            task.cancel()
        for task in list(self._reader_tasks):
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
        self._reader_tasks.clear()
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
        self._server = None

    async def submit_payload(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        """Submit a candidate payload; resolves to the committed ledger block."""
        if self._server is None:
            raise RuntimeError("Consensus node not started")
        payload_dict = dict(payload)
        future: asyncio.Future[LedgerBlock] = asyncio.get_running_loop().create_future()
        async with self._state_mu:
            idx = self._height.index
            self._commit_waiters.setdefault(idx, []).append(future)
        await self._submit_candidate(_ProposalCandidate(from_id=self.node_id, payload=payload_dict))
        blk = await future
        return dict(blk)

    async def _submit_candidate(self, cand: _ProposalCandidate) -> None:
        async with self._state_mu:
            idx = self._height.index
            self._pending.setdefault(idx, []).append(cand)
            leader = self._leader_for_index(idx)
            if leader == self.node_id:
                if idx not in self._propose_tasks:
                    self._propose_tasks[idx] = asyncio.create_task(self._propose_after_grace(idx), name=f"bft-propose:{self.node_id}:{idx}")
                return
        await self._send_to_peer(leader, {"type": "PROPOSE_REQUEST", "from": self.node_id, "index": idx, "payload": cand.payload})

    def _leader_for_index(self, index: int) -> str:
        ids = sorted(n["id"] for n in self._nodes if n["id"] not in self._quarantined_peers)
        if not ids:
            return self.node_id
        return ids[index % len(ids)]

    def _quorum(self) -> int:
        n = len(self._nodes)
        f = max(0, (n - 1) // 3)
        return (2 * f) + 1

    async def _propose_after_grace(self, index: int) -> None:
        try:
            await asyncio.sleep(self.proposal_grace_ms / 1000.0)
            async with self._state_mu:
                if self._height.index != index or self._height.proposal is not None:
                    return
                candidates = list(self._pending.get(index, []))
                if not candidates:
                    return
                chosen = min(candidates, key=lambda c: c.stable_key())
                block = self._build_block(index=index, prev_hash=self._height.prev_hash, payload=chosen.payload)
                self._height.proposal = block
                self._height.prepares.add(self.node_id)
            await self._broadcast({"type": "PROPOSE_BLOCK", "from": self.node_id, "block": block})
            await self._broadcast({"type": "PREPARE", "from": self.node_id, "index": index, "block_hash": block["hash"]})
            await self._maybe_commit(index=index, block=block)
        finally:
            async with self._state_mu:
                self._propose_tasks.pop(index, None)

    def _build_block(self, *, index: int, prev_hash: str, payload: Mapping[str, Any]) -> LedgerBlock:
        header: MutableMapping[str, Any] = {
            "index": index,
            "ts_utc": _now_ts_utc(),
            "execution_token": self.execution_token,
            "prev_hash": prev_hash,
            "payload": dict(payload),
        }
        h = _compute_block_hash(cast(Mapping[str, Any], header))
        header["hash"] = h
        header["signature"] = _compute_block_signature(cast(Mapping[str, Any], header))
        return cast(LedgerBlock, dict(header))

    async def _handle_inbound(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        peer = _PeerConn(writer=writer, is_outbound=False)
        task = asyncio.create_task(self._peer_read_loop(reader, peer), name=f"bft-peer:{self.node_id}:{peer.addr}")
        self._reader_tasks.add(task)
        try:
            await task
        finally:
            self._reader_tasks.discard(task)

    async def _peer_read_loop(self, reader: asyncio.StreamReader, peer: _PeerConn) -> None:
        try:
            await self._send_raw(peer, {"type": "HELLO", "from": self.node_id, "cluster_id": self._cluster_id})
            while not reader.at_eof() and not self._closed:
                raw = await reader.readline()
                if not raw:
                    break
                try:
                    msg = json.loads(raw.decode("utf-8", errors="replace"))
                except Exception:
                    continue
                if not isinstance(msg, dict):
                    continue
                await self._on_message(cast(Mapping[str, Any], msg), peer)
        except asyncio.CancelledError:
            raise
        except _DropConnection:
            pass
        except ByzantineNodeException as exc:
            await self._quarantine_connection(peer, exc)
        except Exception:
            pass
        finally:
            try:
                peer.writer.close()
            except Exception:
                pass
            if peer.peer_id:
                async with self._peers_mu:
                    cur = self._peers.get(peer.peer_id)
                    if cur is peer:
                        self._peers.pop(peer.peer_id, None)

    async def _on_message(self, msg: Mapping[str, Any], peer: _PeerConn) -> None:
        mtype = msg.get("type")
        if not isinstance(mtype, str):
            return
        if mtype == "HELLO":
            await self._handle_hello(msg, peer)
            return
        if peer.peer_id is None:
            return
        if mtype == "PROPOSE_REQUEST":
            await self._handle_propose_request(msg, peer)
            return
        if mtype == "PROPOSE_BLOCK":
            await self._handle_propose_block(msg, peer)
            return
        if mtype == "PREPARE":
            await self._handle_prepare(msg, peer)
            return
        if mtype == "COMMIT":
            await self._handle_commit(msg, peer)
            return

    async def _handle_hello(self, msg: Mapping[str, Any], peer: _PeerConn) -> None:
        peer_id = msg.get("from")
        cluster_id = msg.get("cluster_id")
        if not isinstance(peer_id, str) or not peer_id:
            return
        if not isinstance(cluster_id, str) or cluster_id != self._cluster_id:
            raise ByzantineNodeException("HELLO cluster_id mismatch", peer_id=peer_id, details={"cluster_id": cluster_id})
        if peer_id == self.node_id:
            return
        if self._peer_is_blocked(peer_id):
            raise _DropConnection("Peer blocked by partition policy")
        peer.peer_id = peer_id
        async with self._peers_mu:
            existing = self._peers.get(peer_id)
            preferred_outbound = self.node_id < peer_id
            if existing is None:
                if peer.is_outbound != preferred_outbound:
                    # Keep a single deterministic direction between peers.
                    raise _DropConnection("Non-preferred connection direction")
                self._peers[peer_id] = peer
                return
            if existing.is_outbound == preferred_outbound:
                # Existing matches preference; drop the new connection.
                raise _DropConnection("Duplicate connection")
            # Replace with preferred direction.
            try:
                existing.writer.close()
            except Exception:
                pass
            if peer.is_outbound != preferred_outbound:
                raise _DropConnection("Non-preferred connection direction")
            self._peers[peer_id] = peer

    async def _handle_propose_request(self, msg: Mapping[str, Any], peer: _PeerConn) -> None:
        idx = msg.get("index")
        payload = msg.get("payload")
        if not isinstance(idx, int):
            return
        if not isinstance(payload, dict):
            return
        async with self._state_mu:
            if self._leader_for_index(idx) != self.node_id:
                return
            if idx != self._height.index:
                # Lagging proposer; treat as orphaned request.
                self._record_orphaned(
                    kind="ORPHANED_PROPOSE_REQUEST",
                    peer_id=peer.peer_id,
                    details={"index": idx, "expected_index": self._height.index, "payload": payload},
                )
                return
            self._pending.setdefault(idx, []).append(_ProposalCandidate(from_id=peer.peer_id or "peer", payload=cast(Mapping[str, Any], payload)))
            if idx not in self._propose_tasks and self._height.proposal is None:
                self._propose_tasks[idx] = asyncio.create_task(self._propose_after_grace(idx), name=f"bft-propose:{self.node_id}:{idx}")

    async def _handle_propose_block(self, msg: Mapping[str, Any], peer: _PeerConn) -> None:
        blk_obj = msg.get("block")
        blk = _coerce_block(blk_obj)
        if blk is None:
            raise ByzantineNodeException("Invalid block schema", peer_id=peer.peer_id, details={"block": blk_obj})
        index = int(blk["index"])
        leader = self._leader_for_index(index)
        if peer.peer_id != leader:
            async with self._state_mu:
                expected_index = self._height.index
                expected_prev = self._height.prev_hash
            if index != expected_index or str(blk.get("prev_hash")) != expected_prev:
                raise ByzantineNodeException(
                    "Non-leader proposal violates local head",
                    peer_id=peer.peer_id,
                    details={"index": index, "expected_index": expected_index, "prev_hash": blk.get("prev_hash"), "expected_prev_hash": expected_prev, "block": blk},
                )
            self._record_orphaned(
                kind="ORPHANED_NON_LEADER_PROPOSAL",
                peer_id=peer.peer_id,
                details={"expected_leader": leader, "block": blk},
            )
            return
        with ReadOnlyWorkspaceGuard(self.repo_root):
            self._verify_pre_prepare(blk, peer_id=peer.peer_id)
        async with self._state_mu:
            if index != self._height.index:
                raise ByzantineNodeException(
                    "Unexpected proposal index",
                    peer_id=peer.peer_id,
                    details={"index": index, "expected_index": self._height.index, "block": blk},
                )
            if str(blk.get("prev_hash")) != self._height.prev_hash:
                raise ByzantineNodeException(
                    "Unexpected proposal prev_hash",
                    peer_id=peer.peer_id,
                    details={"index": index, "prev_hash": blk.get("prev_hash"), "expected_prev_hash": self._height.prev_hash, "block": blk},
                )
            if self._height.proposal is None:
                self._height.proposal = blk
            elif self._height.proposal.get("hash") != blk.get("hash"):
                raise ByzantineNodeException(
                    "Conflicting proposal at same height",
                    peer_id=peer.peer_id,
                    details={"existing": self._height.proposal, "incoming": blk},
                )
            self._height.prepares.add(self.node_id)
        await self._broadcast({"type": "PREPARE", "from": self.node_id, "index": index, "block_hash": blk["hash"]})
        await self._maybe_commit(index=index, block=blk)

    def _verify_pre_prepare(self, block: LedgerBlock, *, peer_id: str | None) -> None:
        idx = int(block.get("index", -1))
        if not _block_is_self_consistent(block):
            raise ByzantineNodeException("Block hash/signature invalid", peer_id=peer_id, details={"block": block})
        want_token = self.execution_token
        if str(block.get("execution_token") or "") != want_token:
            raise ByzantineNodeException(
                "Execution token mismatch",
                peer_id=peer_id,
                details={"token": block.get("execution_token"), "expected": want_token, "block": block},
            )
        # Continuity is checked against local head; a lagging/malicious peer is quarantined.
        if not isinstance(block.get("prev_hash"), str) or not _looks_like_hash(str(block.get("prev_hash")), n=64):
            raise ByzantineNodeException("prev_hash malformed", peer_id=peer_id, details={"block": block})
        # The strict head check happens under the state lock in _handle_propose_block; keep a redundancy check here.
        if idx < 0:
            raise ByzantineNodeException("Index malformed", peer_id=peer_id, details={"block": block})

    async def _handle_prepare(self, msg: Mapping[str, Any], peer: _PeerConn) -> None:
        idx = msg.get("index")
        bh = msg.get("block_hash")
        if not isinstance(idx, int) or not isinstance(bh, str) or not _looks_like_hash(bh, n=64):
            return
        async with self._state_mu:
            if idx != self._height.index:
                return
            if self._height.proposal is None:
                return
            if self._height.proposal.get("hash") != bh:
                raise ByzantineNodeException(
                    "Prepare hash mismatch",
                    peer_id=peer.peer_id,
                    details={"index": idx, "block_hash": bh, "expected": self._height.proposal.get("hash")},
                )
            if peer.peer_id:
                self._height.prepares.add(peer.peer_id)
            block = self._height.proposal
        await self._maybe_commit(index=idx, block=cast(LedgerBlock, block))

    async def _handle_commit(self, msg: Mapping[str, Any], peer: _PeerConn) -> None:
        idx = msg.get("index")
        bh = msg.get("block_hash")
        if not isinstance(idx, int) or not isinstance(bh, str) or not _looks_like_hash(bh, n=64):
            return
        async with self._state_mu:
            if idx != self._height.index:
                return
            if self._height.proposal is None or self._height.proposal.get("hash") != bh:
                return
            if peer.peer_id:
                self._height.commits.add(peer.peer_id)
            self._height.commits.add(self.node_id)
            commit_count = len(self._height.commits)
            block = self._height.proposal
        if commit_count >= self._quorum():
            await self._commit_block(cast(LedgerBlock, block))

    async def _maybe_commit(self, *, index: int, block: LedgerBlock) -> None:
        async with self._state_mu:
            if index != self._height.index or self._height.committed:
                return
            prepare_count = len(self._height.prepares)
        if prepare_count >= self._quorum():
            await self._broadcast({"type": "COMMIT", "from": self.node_id, "index": index, "block_hash": block["hash"]})
            await self._commit_block(block)

    async def _commit_block(self, block: LedgerBlock) -> None:
        async with self._state_mu:
            if self._height.committed:
                return
            if int(block.get("index", -1)) != self._height.index:
                return
            if str(block.get("prev_hash")) != self._height.prev_hash:
                raise ByzantineNodeException(
                    "Commit continuity mismatch",
                    peer_id=None,
                    details={"block": block, "expected_prev_hash": self._height.prev_hash},
                )
            self._height.committed = True
            pending = list(self._pending.get(self._height.index, []))
            waiters = self._commit_waiters.pop(self._height.index, [])
        await asyncio.to_thread(_append_jsonl_atomic, self._ledger_path, cast(Mapping[str, Any], block))
        for cand in pending:
            if dict(cand.payload) != cast(dict[str, Any], block.get("payload", {})):
                self._record_orphaned(
                    kind="ORPHANED_PROPOSAL_NOT_SELECTED",
                    peer_id=cand.from_id,
                    details={"index": block["index"], "candidate_payload": cand.payload, "chosen_payload": block.get("payload")},
                )
        for fut in waiters:
            if not fut.done():
                fut.set_result(block)
        async with self._state_mu:
            # Advance height and clear per-height state.
            self._pending.pop(self._height.index, None)
            self._height = _ConsensusHeight(index=self._height.index + 1, prev_hash=str(block["hash"]))
            # If we are leader for the new index and already have pending candidates, schedule.
            idx = self._height.index
            if self._leader_for_index(idx) == self.node_id and idx in self._pending and idx not in self._propose_tasks:
                self._propose_tasks[idx] = asyncio.create_task(self._propose_after_grace(idx), name=f"bft-propose:{self.node_id}:{idx}")

    async def _quarantine_connection(self, peer: _PeerConn, exc: ByzantineNodeException) -> None:
        pid = peer.peer_id or exc.peer_id
        if pid:
            self.quarantine_peer(pid)
        peer.quarantined = True
        self._record_orphaned(
            kind="QUARANTINED",
            peer_id=pid,
            details={"addr": peer.addr, "error": str(exc), "details": getattr(exc, "details", None)},
        )
        try:
            peer.writer.close()
        except Exception:
            pass

    def _record_orphaned(self, *, kind: str, peer_id: str | None, details: Mapping[str, Any]) -> None:
        record: dict[str, Any] = {
            "ts_utc": _now_ts_utc(),
            "kind": kind,
            "peer_id": peer_id or "unknown",
            "details": dict(details),
        }
        try:
            _append_jsonl_atomic(self._orphaned_path, record)
        except Exception:
            pass

    async def _reconnect_loop(self) -> None:
        while not self._closed:
            for node in self._nodes:
                pid = node["id"]
                if pid == self.node_id:
                    continue
                if self._peer_is_blocked(pid):
                    continue
                async with self._peers_mu:
                    if pid in self._peers:
                        continue
                await self._dial_peer(pid, host=node["host"], port=int(node["port"]))
            await self._gossip_progress()
            await asyncio.sleep(self.reconnect_interval_ms / 1000.0)

    async def _gossip_progress(self) -> None:
        async with self._state_mu:
            idx = self._height.index
            proposal = self._height.proposal
            committed = self._height.committed
            leader = self._leader_for_index(idx)
            has_pending = bool(self._pending.get(idx))
            has_propose_task = idx in self._propose_tasks
        if committed:
            return
        if proposal is not None:
            bh = str(proposal.get("hash") or "")
            if _looks_like_hash(bh, n=64):
                await self._broadcast({"type": "PREPARE", "from": self.node_id, "index": idx, "block_hash": bh})
                if leader == self.node_id:
                    await self._broadcast({"type": "PROPOSE_BLOCK", "from": self.node_id, "block": proposal})
            return
        if leader == self.node_id and has_pending and not has_propose_task:
            async with self._state_mu:
                if idx == self._height.index and self._height.proposal is None and idx not in self._propose_tasks:
                    self._propose_tasks[idx] = asyncio.create_task(
                        self._propose_after_grace(idx),
                        name=f"bft-propose:{self.node_id}:{idx}",
                    )

    async def _dial_peer(self, peer_id: str, *, host: str, port: int) -> None:
        preferred_outbound = self.node_id < peer_id
        if not preferred_outbound:
            return
        if self._peer_is_blocked(peer_id):
            return
        try:
            reader, writer = await asyncio.open_connection(host=host, port=port)
        except Exception:
            return
        peer = _PeerConn(writer=writer, is_outbound=True)
        task = asyncio.create_task(self._peer_read_loop(reader, peer), name=f"bft-peer:{self.node_id}:{peer_id}:{peer.addr}")
        self._reader_tasks.add(task)
        # Note: registration occurs once HELLO is exchanged; the read loop sends our HELLO immediately.

    async def _broadcast(self, msg: Mapping[str, Any]) -> None:
        async with self._peers_mu:
            peers = list(self._peers.items())
        await asyncio.gather(*(self._send_raw(peer, msg) for _, peer in peers), return_exceptions=True)

    async def _send_to_peer(self, peer_id: str, msg: Mapping[str, Any]) -> None:
        if self._peer_is_blocked(peer_id):
            return
        async with self._peers_mu:
            peer = self._peers.get(peer_id)
        if peer is None:
            return
        await self._send_raw(peer, msg)

    async def _send_raw(self, peer: _PeerConn, msg: Mapping[str, Any]) -> None:
        if peer.quarantined:
            return
        if peer.peer_id and self._peer_is_blocked(peer.peer_id):
            return
        if self.drop_rate > 0.0 and self._rng.random() < self.drop_rate:
            return
        if self.jitter_ms > 0:
            await asyncio.sleep(self._rng.randint(0, self.jitter_ms) / 1000.0)
        data = (_canonical_json(dict(msg)) + "\n").encode("utf-8")
        try:
            async with peer.send_mu:
                peer.writer.write(data)
                await peer.writer.drain()
        except Exception:
            try:
                peer.writer.close()
            except Exception:
                pass

    @staticmethod
    def _load_topology(path: Path) -> _ClusterTopology:
        raw = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        if not isinstance(raw, dict):
            raise ValueError("cluster_topology must be a JSON object")
        cluster_id = raw.get("cluster_id") or "cluster"
        nodes_raw = raw.get("nodes")
        if not isinstance(cluster_id, str) or not cluster_id:
            raise ValueError("cluster_id must be a non-empty string")
        if not isinstance(nodes_raw, list) or not nodes_raw:
            raise ValueError("nodes must be a non-empty list")
        nodes: list[_TopologyNode] = []
        for item in nodes_raw:
            if not isinstance(item, dict):
                continue
            nid = item.get("id")
            host = item.get("host")
            port = item.get("port")
            if not isinstance(nid, str) or not nid:
                continue
            if not isinstance(host, str) or not host:
                continue
            if not isinstance(port, int) or port <= 0 or port > 65535:
                continue
            nodes.append(cast(_TopologyNode, {"id": nid, "host": host, "port": port}))
        if not nodes:
            raise ValueError("No valid nodes in topology")
        return cast(_ClusterTopology, {"cluster_id": cluster_id, "nodes": nodes})


def pick_free_port() -> int:
    """Test helper: allocate a free TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        return int(s.getsockname()[1])
