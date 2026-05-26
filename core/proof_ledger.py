"""Immutable, log-structured cryptographic proof ledger (stdlib-only, Python 3.10+).

The proof ledger is an append-only JSONL file intended for deterministic forensic
replay. Each line is a self-contained block with:
  - auto-incrementing index
  - high-resolution UTC timestamp (ISO-8601, microseconds, Z suffix)
  - execution token
  - previous block hash (SHA-256)
  - current block hash (SHA-256 over canonical JSON of block header + payload)
  - final aggregated 32-bit FNV-1a signature over the entire block (excluding signature)
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping, MutableMapping, TypedDict, cast

from core.hashutil import fnv1a_32


def _canonical_json(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _utc_timestamp() -> str:
    # RFC 3339-ish; stable, parseable, microsecond resolution.
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


class ProofLedgerBlock(TypedDict):
    index: int
    ts_utc: str
    execution_token: str
    prev_hash: str
    payload: object
    hash: str
    signature: str


def _compute_block_hash(block_without_hash_and_sig: Mapping[str, Any]) -> str:
    material = _canonical_json(block_without_hash_and_sig).encode("utf-8", errors="surrogatepass")
    return hashlib.sha256(material).hexdigest()


def _compute_block_signature(block_without_sig: Mapping[str, Any]) -> str:
    return fnv1a_32(_canonical_json(block_without_sig))


@dataclass(slots=True)
class ProofLedgerManager:
    """Append-only proof ledger writer with deterministic block signing."""

    logs_dir: Path
    execution_token: str

    def __post_init__(self) -> None:
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self._path = self.logs_dir / "PROOFS_LEDGER.jsonl"
        self._mu = threading.Lock()
        self._next_index = 0
        self._prev_hash = "0" * 64
        self._hydrate_tail()

    @property
    def path(self) -> Path:
        return self._path

    def _hydrate_tail(self) -> None:
        try:
            if not self._path.exists():
                return
            lines = self._path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return
        for raw in reversed(lines):
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except Exception:
                continue
            if not isinstance(obj, dict):
                continue
            idx = obj.get("index")
            h = obj.get("hash")
            if isinstance(idx, int) and isinstance(h, str) and len(h) == 64:
                self._next_index = idx + 1
                self._prev_hash = h
                return

    def append_block(self, payload: Mapping[str, Any]) -> ProofLedgerBlock:
        """Append a signed block and return the materialized block."""
        with self._mu:
            header: MutableMapping[str, Any] = {
                "index": self._next_index,
                "ts_utc": _utc_timestamp(),
                "execution_token": self.execution_token,
                "prev_hash": self._prev_hash,
                "payload": dict(payload),
            }
            block_hash = _compute_block_hash(header)
            header["hash"] = block_hash
            signature = _compute_block_signature(header)
            header["signature"] = signature

            line = _canonical_json(header)
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
                f.flush()
                try:
                    os.fsync(f.fileno())
                except OSError:
                    pass

            self._prev_hash = block_hash
            self._next_index += 1
            return cast(ProofLedgerBlock, dict(header))


def iter_ledger_blocks(path: Path) -> Iterator[ProofLedgerBlock]:
    """Iterate blocks from a JSONL ledger file (best-effort parsing)."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return iter(())
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            obj = json.loads(ln)
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        yield cast(ProofLedgerBlock, obj)


def verify_ledger_blocks(blocks: Iterator[ProofLedgerBlock]) -> list[ProofLedgerBlock]:
    """Verify hash chain + FNV signature; returns verified blocks or raises ValueError."""
    verified: list[ProofLedgerBlock] = []
    prev_hash = "0" * 64
    expected_index = 0
    for block in blocks:
        idx = block.get("index")
        if idx != expected_index:
            raise ValueError(f"Ledger index mismatch: expected={expected_index} got={idx}")
        if block.get("prev_hash") != prev_hash:
            raise ValueError(f"Ledger chain mismatch at index={idx}")

        # Recompute hash.
        header = {
            "index": block.get("index"),
            "ts_utc": block.get("ts_utc"),
            "execution_token": block.get("execution_token"),
            "prev_hash": block.get("prev_hash"),
            "payload": block.get("payload"),
        }
        want_hash = _compute_block_hash(cast(Mapping[str, Any], header))
        if block.get("hash") != want_hash:
            raise ValueError(f"Ledger hash mismatch at index={idx}")

        header_with_hash = dict(header)
        header_with_hash["hash"] = want_hash
        want_sig = _compute_block_signature(cast(Mapping[str, Any], header_with_hash))
        if block.get("signature") != want_sig:
            raise ValueError(f"Ledger signature mismatch at index={idx}")

        prev_hash = want_hash
        expected_index += 1
        verified.append(block)
    return verified

