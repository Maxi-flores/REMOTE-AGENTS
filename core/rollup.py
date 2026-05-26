"""Transaction rollup + cryptographic state compression (stdlib-only, Python 3.10+).

The consensus ledger is optimized for atomic ordering of *blocks*, not for
high-frequency telemetry. This module batches local execution traces into a
single rollup payload that is:
  - deterministic (canonical JSON materialization)
  - verifiable (Merkle root + bound metadata "proof")
  - zero-dependency (hashlib + json only)
  - thread-safe (single lock protecting in-memory buffers and journal writes)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any, Iterable, Mapping, MutableMapping, Sequence, TypedDict, cast

from core.cache import CacheDecision
from core.telemetry import TelemetryRecord


def _canonical_json(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _looks_like_hash(value: str, *, n: int) -> bool:
    if not isinstance(value, str) or len(value) != n:
        return False
    for ch in value:
        if ch not in "0123456789abcdef":
            return False
    return True


class RollupTransaction(TypedDict):
    seq: int
    ts: float
    correlation_id: str
    event: str
    wall_ms: float
    cpu_ms: float
    bytes_transferred: int


class RollupProof(TypedDict):
    previous_ledger_root: str
    target_ledger_root: str
    correlation_mask: str
    execution_token_hash: str
    proof_hash: str


class RollupPayload(TypedDict):
    kind: str  # "ROLLUP_BLOCK"
    batch_id: str
    seq_start: int
    seq_end: int
    tx_count: int
    previous_ledger_root: str
    merkle_root: str
    correlation_mask: str
    execution_token_hash: str
    target_ledger_root: str
    zk_proof: RollupProof
    algo: str


def compute_correlation_mask(correlation_ids: Iterable[str], *, bits: int = 256) -> str:
    """Compute a deterministic bitmask for a set of correlation_ids.

    This is a compact, non-reversible representation to bind membership. The
    mask is *not* a bloom filter; it's a fixed-size bitset indexed by a stable
    hash.
    """

    if bits <= 0 or bits % 8 != 0:
        raise ValueError("bits must be a positive multiple of 8")
    out = bytearray(bits // 8)
    for cid in correlation_ids:
        digest = hashlib.sha256(str(cid).encode("utf-8", errors="surrogatepass")).digest()
        bit = int.from_bytes(digest[:2], "big") % bits
        out[bit // 8] |= 1 << (bit % 8)
    return bytes(out).hex()


def compute_execution_token_hash(*, wall_ms: float, cpu_ms: float, bytes_transferred: int) -> str:
    material = _canonical_json(
        {
            "wall_ms": float(wall_ms),
            "cpu_ms": float(cpu_ms),
            "bytes_transferred": int(bytes_transferred),
        }
    ).encode("utf-8", errors="surrogatepass")
    return _sha256_hex(material)


def merkle_root_from_transactions(txs: Sequence[Mapping[str, Any]]) -> str:
    """Compile a deterministic Merkle root from a list of transactions."""

    if not txs:
        return _sha256_hex(b"ROLLUP:EMPTY")

    def _material(tx: Mapping[str, Any]) -> Mapping[str, Any]:
        # Only bind deterministic fields. The journal may store wall-clock
        # timestamps and local sequencing for debugging, but they must not affect
        # verification.
        return {
            "correlation_id": str(tx.get("correlation_id") or ""),
            "event": str(tx.get("event") or ""),
            "wall_ms": float(tx.get("wall_ms") or 0.0),
            "cpu_ms": float(tx.get("cpu_ms") or 0.0),
            "bytes_transferred": int(tx.get("bytes_transferred") or 0),
        }

    def _stable_key(tx: Mapping[str, Any]) -> tuple[str, str, int, int, int]:
        material = _material(tx)
        return (
            str(material["correlation_id"]),
            str(material["event"]),
            int(material["bytes_transferred"]),
            int(float(material["wall_ms"]) * 1_000_000),
            int(float(material["cpu_ms"]) * 1_000_000),
        )

    ordered = sorted(txs, key=_stable_key)

    level: list[bytes] = []
    for tx in ordered:
        leaf_material = _canonical_json(dict(_material(tx))).encode("utf-8", errors="surrogatepass")
        level.append(hashlib.sha256(b"L" + leaf_material).digest())

    # Balanced binary tree by pairwise hashing; duplicate last hash on odd width.
    while len(level) > 1:
        if len(level) % 2 == 1:
            level.append(level[-1])
        parents: list[bytes] = []
        for i in range(0, len(level), 2):
            parents.append(hashlib.sha256(b"I" + level[i] + level[i + 1]).digest())
        level = parents
    return level[0].hex()


def compute_target_ledger_root(
    *,
    previous_ledger_root: str,
    merkle_root: str,
    correlation_mask: str,
    execution_token_hash: str,
    seq_start: int,
    seq_end: int,
    tx_count: int,
) -> str:
    payload = _canonical_json(
        {
            "previous_ledger_root": previous_ledger_root,
            "merkle_root": merkle_root,
            "correlation_mask": correlation_mask,
            "execution_token_hash": execution_token_hash,
            "seq_start": int(seq_start),
            "seq_end": int(seq_end),
            "tx_count": int(tx_count),
        }
    ).encode("utf-8", errors="surrogatepass")
    return _sha256_hex(payload)


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


def iter_rollup_journal(path: Path) -> Iterable[RollupTransaction]:
    if not path.exists():
        return ()
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ()
    out: list[RollupTransaction] = []
    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        seq = obj.get("seq")
        if not isinstance(seq, int) or isinstance(seq, bool) or seq <= 0:
            continue
        cid = obj.get("correlation_id")
        ev = obj.get("event")
        if not isinstance(cid, str) or not cid:
            continue
        if not isinstance(ev, str) or not ev:
            continue
        out.append(
            cast(
                RollupTransaction,
                {
                    "seq": int(seq),
                    "ts": float(obj.get("ts") or 0.0),
                    "correlation_id": str(cid),
                    "event": str(ev),
                    "wall_ms": float(obj.get("wall_ms") or 0.0),
                    "cpu_ms": float(obj.get("cpu_ms") or 0.0),
                    "bytes_transferred": int(obj.get("bytes_transferred") or 0),
                },
            )
        )
    return out


def verify_rollup_payload(*, payload: Mapping[str, Any], journal_path: Path, expected_prev_root: str) -> RollupPayload:
    """Recompute rollup material from the local mirror journal and verify fields."""

    if payload.get("kind") != "ROLLUP_BLOCK":
        raise ValueError("payload kind is not ROLLUP_BLOCK")

    algo = payload.get("algo")
    if not isinstance(algo, str) or not algo:
        raise ValueError("algo missing")
    if algo != "sha256/merkle:v1":
        raise ValueError("algo unsupported")

    seq_start = payload.get("seq_start")
    seq_end = payload.get("seq_end")
    tx_count = payload.get("tx_count")
    prev_root = payload.get("previous_ledger_root")
    merkle_root = payload.get("merkle_root")
    corr_mask = payload.get("correlation_mask")
    token_hash = payload.get("execution_token_hash")
    target_root = payload.get("target_ledger_root")
    zk_proof = payload.get("zk_proof")

    if not isinstance(seq_start, int) or isinstance(seq_start, bool) or seq_start <= 0:
        raise ValueError("seq_start invalid")
    if not isinstance(seq_end, int) or isinstance(seq_end, bool) or seq_end < seq_start:
        raise ValueError("seq_end invalid")
    if not isinstance(tx_count, int) or isinstance(tx_count, bool) or tx_count <= 0:
        raise ValueError("tx_count invalid")
    if not isinstance(prev_root, str) or not _looks_like_hash(prev_root, n=64):
        raise ValueError("previous_ledger_root invalid")
    if not isinstance(merkle_root, str) or not _looks_like_hash(merkle_root, n=64):
        raise ValueError("merkle_root invalid")
    if not isinstance(corr_mask, str) or not _looks_like_hash(corr_mask, n=64):
        raise ValueError("correlation_mask invalid")
    if not isinstance(token_hash, str) or not _looks_like_hash(token_hash, n=64):
        raise ValueError("execution_token_hash invalid")
    if not isinstance(target_root, str) or not _looks_like_hash(target_root, n=64):
        raise ValueError("target_ledger_root invalid")
    if not isinstance(zk_proof, dict):
        raise ValueError("zk_proof invalid")

    if prev_root != expected_prev_root:
        raise ValueError("previous_ledger_root does not match block prev_hash")

    txs = [t for t in iter_rollup_journal(journal_path) if seq_start <= t["seq"] <= seq_end]
    if len(txs) != int(tx_count):
        raise ValueError(f"tx_count mismatch: journal has {len(txs)} records")

    txs.sort(key=lambda t: (t["correlation_id"], t["event"], int(t["bytes_transferred"])))

    recomputed_merkle = merkle_root_from_transactions(txs)
    if recomputed_merkle != merkle_root:
        raise ValueError("merkle_root mismatch")

    recomputed_mask = compute_correlation_mask((t["correlation_id"] for t in txs))
    if recomputed_mask != corr_mask:
        raise ValueError("correlation_mask mismatch")

    total_wall = sum(float(t["wall_ms"]) for t in txs)
    total_cpu = sum(float(t["cpu_ms"]) for t in txs)
    total_bytes = sum(int(t["bytes_transferred"]) for t in txs)
    recomputed_token = compute_execution_token_hash(wall_ms=total_wall, cpu_ms=total_cpu, bytes_transferred=total_bytes)
    if recomputed_token != token_hash:
        raise ValueError("execution_token_hash mismatch")

    recomputed_target = compute_target_ledger_root(
        previous_ledger_root=prev_root,
        merkle_root=merkle_root,
        correlation_mask=corr_mask,
        execution_token_hash=token_hash,
        seq_start=seq_start,
        seq_end=seq_end,
        tx_count=tx_count,
    )
    if recomputed_target != target_root:
        raise ValueError("target_ledger_root mismatch")

    # Lightweight simulated ZK-proof: bind to key structural fields.
    if str(zk_proof.get("previous_ledger_root") or "") != prev_root:
        raise ValueError("zk_proof previous_ledger_root mismatch")
    if str(zk_proof.get("target_ledger_root") or "") != target_root:
        raise ValueError("zk_proof target_ledger_root mismatch")
    if str(zk_proof.get("correlation_mask") or "") != corr_mask:
        raise ValueError("zk_proof correlation_mask mismatch")
    if str(zk_proof.get("execution_token_hash") or "") != token_hash:
        raise ValueError("zk_proof execution_token_hash mismatch")
    proof_hash = zk_proof.get("proof_hash")
    if not isinstance(proof_hash, str) or not _looks_like_hash(proof_hash, n=64):
        raise ValueError("zk_proof proof_hash invalid")
    proof_material = _canonical_json(
        {
            "previous_ledger_root": prev_root,
            "target_ledger_root": target_root,
            "correlation_mask": corr_mask,
            "execution_token_hash": token_hash,
        }
    ).encode("utf-8", errors="surrogatepass")
    if _sha256_hex(proof_material) != proof_hash:
        raise ValueError("zk_proof proof_hash mismatch")

    return cast(RollupPayload, dict(payload))


@dataclass(frozen=True, slots=True)
class RollupCommitResult:
    committed_block: Mapping[str, Any]
    rollup_payload: RollupPayload


class WorkspaceRollupEngine:
    """Thread-safe batching engine that submits compressed rollups to consensus."""

    def __init__(self, *, log_dir: Path, batch_size: int = 100, journal_name: str = "ROLLUP_JOURNAL.jsonl") -> None:
        if batch_size <= 0:
            raise ValueError("batch_size must be > 0")
        self._log_dir = log_dir.resolve()
        self._journal_path = (self._log_dir / journal_name).resolve()
        self._batch_size = int(batch_size)
        self._mu = Lock()
        self._next_seq = 1
        self._pending: list[RollupTransaction] = []
        self._waiters: list[asyncio.Future[RollupCommitResult]] = []
        self._batch_counter = 0

    @property
    def journal_path(self) -> Path:
        return self._journal_path

    @property
    def batch_size(self) -> int:
        return self._batch_size

    def ingest_cache_decision(
        self,
        *,
        correlation_id: str,
        decision: CacheDecision,
        event: str | None = None,
    ) -> RollupTransaction:
        ev = event or str(decision.cache_state)
        t = decision.telemetry
        return self.ingest_transaction(
            correlation_id=correlation_id,
            event=ev,
            wall_ms=float(t.wall_ms),
            cpu_ms=float(t.cpu_ms),
            bytes_transferred=int(t.bytes_transferred),
        )

    def ingest_telemetry_record(self, *, record: TelemetryRecord) -> RollupTransaction:
        return self.ingest_transaction(
            correlation_id=record.correlation_id,
            event=record.event,
            wall_ms=float(record.latency_ms),
            cpu_ms=0.0,
            bytes_transferred=int(record.payload_bytes),
        )

    def ingest_transaction(
        self,
        *,
        correlation_id: str,
        event: str,
        wall_ms: float,
        cpu_ms: float,
        bytes_transferred: int,
    ) -> RollupTransaction:
        """Record a transaction locally and append it to the mirror journal."""

        now = time.time()
        with self._mu:
            seq = self._next_seq
            self._next_seq += 1
            tx: RollupTransaction = {
                "seq": int(seq),
                "ts": float(now),
                "correlation_id": str(correlation_id),
                "event": str(event),
                "wall_ms": float(wall_ms),
                "cpu_ms": float(cpu_ms),
                "bytes_transferred": int(bytes_transferred),
            }
            self._pending.append(tx)
            _append_jsonl_atomic(self._journal_path, tx)
        return tx

    async def submit_transaction(
        self,
        *,
        consensus_node: Any,
        correlation_id: str,
        event: str,
        wall_ms: float,
        cpu_ms: float,
        bytes_transferred: int,
    ) -> RollupCommitResult:
        """Ingest a transaction and await its rollup commit to the consensus ledger."""

        self.ingest_transaction(
            correlation_id=correlation_id,
            event=event,
            wall_ms=wall_ms,
            cpu_ms=cpu_ms,
            bytes_transferred=bytes_transferred,
        )
        fut: asyncio.Future[RollupCommitResult] = asyncio.get_running_loop().create_future()
        batch_to_flush: tuple[list[RollupTransaction], list[asyncio.Future[RollupCommitResult]]] | None = None
        with self._mu:
            self._waiters.append(fut)
            if len(self._pending) >= self._batch_size and len(self._waiters) >= self._batch_size:
                batch = self._pending[: self._batch_size]
                waiters = self._waiters[: self._batch_size]
                self._pending = self._pending[self._batch_size :]
                self._waiters = self._waiters[self._batch_size :]
                batch_to_flush = (batch, waiters)
        if batch_to_flush is not None:
            asyncio.create_task(self._flush_batch(consensus_node, batch_to_flush[0], batch_to_flush[1]))
        return await fut

    async def flush(self, *, consensus_node: Any) -> RollupCommitResult | None:
        """Force-flush the current pending batch (if any)."""

        batch: list[RollupTransaction]
        waiters: list[asyncio.Future[RollupCommitResult]]
        with self._mu:
            if not self._pending:
                return None
            batch = list(self._pending)
            waiters = list(self._waiters)
            self._pending.clear()
            self._waiters.clear()
        return await self._flush_batch(consensus_node, batch, waiters)

    async def _flush_batch(
        self,
        consensus_node: Any,
        txs: Sequence[RollupTransaction],
        waiters: Sequence[asyncio.Future[RollupCommitResult]],
    ) -> RollupCommitResult:
        ordered = sorted(txs, key=lambda t: (t["correlation_id"], t["event"], int(t["bytes_transferred"])))
        seq_start = int(min(t["seq"] for t in ordered))
        seq_end = int(max(t["seq"] for t in ordered))
        tx_count = int(len(ordered))
        with self._mu:
            self._batch_counter += 1
            batch_id = f"{self._batch_counter}:{seq_start}-{seq_end}"

        merkle_root = merkle_root_from_transactions(ordered)
        corr_mask = compute_correlation_mask((t["correlation_id"] for t in ordered))
        total_wall = sum(float(t["wall_ms"]) for t in ordered)
        total_cpu = sum(float(t["cpu_ms"]) for t in ordered)
        total_bytes = sum(int(t["bytes_transferred"]) for t in ordered)
        token_hash = compute_execution_token_hash(wall_ms=total_wall, cpu_ms=total_cpu, bytes_transferred=total_bytes)

        # Bind to the current ledger head as observed at submission time.
        prev_root = "0" * 64
        try:
            ledger_path = Path(getattr(consensus_node, "ledger_path"))
            from core.consensus_node import _hydrate_tail as _consensus_hydrate_tail  # local import to avoid cycles

            _, prev_root = _consensus_hydrate_tail(ledger_path)
        except Exception:
            prev_root = "0" * 64

        target_root = compute_target_ledger_root(
            previous_ledger_root=prev_root,
            merkle_root=merkle_root,
            correlation_mask=corr_mask,
            execution_token_hash=token_hash,
            seq_start=seq_start,
            seq_end=seq_end,
            tx_count=tx_count,
        )

        proof_material = _canonical_json(
            {
                "previous_ledger_root": prev_root,
                "target_ledger_root": target_root,
                "correlation_mask": corr_mask,
                "execution_token_hash": token_hash,
            }
        ).encode("utf-8", errors="surrogatepass")
        proof_hash = _sha256_hex(proof_material)
        zk_proof: RollupProof = {
            "previous_ledger_root": prev_root,
            "target_ledger_root": target_root,
            "correlation_mask": corr_mask,
            "execution_token_hash": token_hash,
            "proof_hash": proof_hash,
        }

        rollup_payload: RollupPayload = {
            "kind": "ROLLUP_BLOCK",
            "batch_id": batch_id,
            "seq_start": seq_start,
            "seq_end": seq_end,
            "tx_count": tx_count,
            "previous_ledger_root": prev_root,
            "merkle_root": merkle_root,
            "correlation_mask": corr_mask,
            "execution_token_hash": token_hash,
            "target_ledger_root": target_root,
            "zk_proof": zk_proof,
            "algo": "sha256/merkle:v1",
        }

        committed = await consensus_node.submit_payload(cast(Mapping[str, Any], rollup_payload))
        res = RollupCommitResult(committed_block=committed, rollup_payload=rollup_payload)
        for fut in waiters:
            if not fut.done():
                fut.set_result(res)
        return res
