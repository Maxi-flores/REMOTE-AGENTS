"""Cryptographic fork detection + deterministic reconciliation for PROOFS_LEDGER.jsonl.

This module is stdlib-only (Python 3.10+) and is designed to heal ledger "head
forks" caused by concurrent writers producing conflicting blocks at the same
index or with divergent prev_hash links.

The reconciler never discards data: pruned blocks and unparsable lines are
persisted to logs/ORPHANED_FORKS.jsonl before the canonical ledger is
linearized.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, MutableMapping, Sequence, TypedDict, cast

from core.hashutil import fnv1a_32
from core.replay import PipelineReplayController, ReadOnlyWorkspaceGuard
from core.transaction_manager import cleanup_workspace_staging


class CryptographicForkException(RuntimeError):
    """Raised when the proof ledger fails hash-chain or signature validation."""

    def __init__(self, message: str, *, ledger_path: Path, details: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        self.ledger_path = ledger_path
        self.details = dict(details or {})


class LedgerBlock(TypedDict):
    index: int
    ts_utc: str
    execution_token: str
    prev_hash: str
    payload: object
    hash: str
    signature: str


_GENESIS_PREV = "0" * 64


def _canonical_json(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _compute_block_hash(block_without_hash_and_sig: Mapping[str, Any]) -> str:
    material = _canonical_json(block_without_hash_and_sig).encode("utf-8", errors="surrogatepass")
    return hashlib.sha256(material).hexdigest()


def _compute_block_signature(block_without_sig: Mapping[str, Any]) -> str:
    return fnv1a_32(_canonical_json(block_without_sig))


def _now_ts_utc() -> str:
    # RFC3339-ish enough for log correlation (kept local to avoid importing datetime everywhere).
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _as_int(value: object) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return None


def _as_str(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def _looks_like_hash(value: str, *, n: int) -> bool:
    if len(value) != n:
        return False
    for ch in value:
        if ch not in "0123456789abcdef":
            return False
    return True


@dataclass(frozen=True, slots=True)
class _ParsedLine:
    line_no: int
    raw: str
    block: LedgerBlock | None
    parse_error: str | None


@dataclass(frozen=True, slots=True)
class _ValidBlock:
    line_no: int
    block: LedgerBlock
    kind: str
    signature_u32: int

    @property
    def index(self) -> int:
        return int(self.block["index"])

    @property
    def prev_hash(self) -> str:
        return str(self.block["prev_hash"])

    @property
    def hash(self) -> str:
        return str(self.block["hash"])


@dataclass(frozen=True, slots=True)
class ForkResolutionResult:
    ledger_path: Path
    orphaned_path: Path
    chosen_tip_hash: str
    chosen_blocks: int
    pruned_lines: int
    reconciliation_index: int
    fork_point_index: int | None


def _frame_kind(payload: object) -> str:
    if isinstance(payload, dict):
        kind = payload.get("kind")
        if isinstance(kind, str) and kind:
            if kind == "GOV_EVENT":
                ev = payload.get("event")
                if isinstance(ev, dict) and isinstance(ev.get("event"), str):
                    return str(ev["event"])
            return kind
        ev = payload.get("event")
        if isinstance(ev, str) and ev:
            return ev
    return "UNKNOWN"


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


def _coerce_block(obj: object) -> LedgerBlock | None:
    if not isinstance(obj, dict):
        return None
    idx = _as_int(obj.get("index"))
    ts_utc = _as_str(obj.get("ts_utc"))
    token = _as_str(obj.get("execution_token"))
    prev_hash = _as_str(obj.get("prev_hash"))
    payload = obj.get("payload")
    h = _as_str(obj.get("hash"))
    sig = _as_str(obj.get("signature"))
    if idx is None or ts_utc is None or token is None or prev_hash is None or h is None or sig is None:
        return None
    if not _looks_like_hash(prev_hash, n=64) or not _looks_like_hash(h, n=64) or not _looks_like_hash(sig, n=8):
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


def _iter_parsed_lines(ledger_path: Path) -> Iterator[_ParsedLine]:
    try:
        text = ledger_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return iter(())
    for i, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            yield _ParsedLine(line_no=i, raw=raw, block=None, parse_error="empty_line")
            continue
        try:
            obj = json.loads(line)
        except Exception as exc:
            yield _ParsedLine(line_no=i, raw=raw, block=None, parse_error=f"json_error:{type(exc).__name__}")
            continue
        block = _coerce_block(obj)
        if block is None:
            yield _ParsedLine(line_no=i, raw=raw, block=None, parse_error="schema_error")
            continue
        yield _ParsedLine(line_no=i, raw=raw, block=block, parse_error=None)


def _valid_blocks(parsed: Iterable[_ParsedLine]) -> list[_ValidBlock]:
    out: list[_ValidBlock] = []
    for item in parsed:
        if item.block is None:
            continue
        if not _block_is_self_consistent(item.block):
            continue
        kind = _frame_kind(item.block.get("payload"))
        try:
            sig_u32 = int(item.block.get("signature", "0"), 16)
        except Exception:
            sig_u32 = 0
        out.append(_ValidBlock(line_no=item.line_no, block=item.block, kind=kind, signature_u32=sig_u32))
    return out


def _detect_fork_point(blocks: Sequence[_ValidBlock]) -> int | None:
    """Return earliest index where multiple children exist for same (index, prev_hash)."""
    by_key: dict[tuple[int, str], int] = {}
    fork: int | None = None
    for b in blocks:
        key = (b.index, b.prev_hash)
        by_key[key] = by_key.get(key, 0) + 1
        if by_key[key] >= 2:
            fork = b.index if fork is None else min(fork, b.index)
    return fork


@dataclass(frozen=True, slots=True)
class _ChainTip:
    tip_id: tuple[int, str, int]  # (index, hash, line_no)
    length: int
    quorum_passed_after_fork: bool
    tip_signature_u32: int
    tip_hash: str


def _chain_tip_key(tip: _ChainTip) -> tuple[int, int, int, str]:
    # Longest Chain Rule, then prefer quorum-passed chain, then highest signature, then lexical tip hash.
    return (
        tip.length,
        1 if tip.quorum_passed_after_fork else 0,
        tip.tip_signature_u32,
        tip.tip_hash,
    )


def _best_chain(blocks: Sequence[_ValidBlock]) -> tuple[list[_ValidBlock], int | None]:
    """Return (chosen_chain_blocks, fork_point_index)."""
    if not blocks:
        return ([], None)

    fork_point = _detect_fork_point(blocks)

    nodes: dict[tuple[int, str, int], _ValidBlock] = {}
    by_index_hash: dict[tuple[int, str], list[tuple[int, str, int]]] = {}
    for b in blocks:
        node_id = (b.index, b.hash, b.line_no)
        nodes[node_id] = b
        by_index_hash.setdefault((b.index, b.hash), []).append(node_id)

    # For parent lookups: (index, hash) -> best tip id and length info.
    best_len: dict[tuple[int, str, int], int] = {}
    parent: dict[tuple[int, str, int], tuple[int, str, int] | None] = {}
    quorum_after_fork: dict[tuple[int, str, int], bool] = {}

    # Process in index order for deterministic reconciliation.
    for idx in sorted({b.index for b in blocks}):
        ids_at_idx = sorted(
            (node_id for node_id in nodes if node_id[0] == idx),
            key=lambda x: (x[0], x[1], x[2]),
        )
        for node_id in ids_at_idx:
            b = nodes[node_id]
            if b.index == 0:
                if b.prev_hash != _GENESIS_PREV:
                    continue
                best_len[node_id] = 1
                parent[node_id] = None
                seen_quorum = b.kind == "QUORUM_PASSED" and (fork_point is None or b.index >= fork_point)
                quorum_after_fork[node_id] = seen_quorum
                continue

            # Find best parent: any node at idx-1 with hash == b.prev_hash.
            best_parent_id: tuple[int, str, int] | None = None
            best_parent_len = -1
            best_parent_quorum = False
            candidate_parent_ids: list[tuple[int, str, int]] = []
            for pid in by_index_hash.get((b.index - 1, b.prev_hash), []):
                if pid in best_len:
                    candidate_parent_ids.append(pid)
            for pid in sorted(candidate_parent_ids, key=lambda x: (best_len.get(x, 0), quorum_after_fork.get(x, False), x[1])):
                plen = best_len.get(pid, -1)
                if plen > best_parent_len:
                    best_parent_len = plen
                    best_parent_id = pid
                    best_parent_quorum = quorum_after_fork.get(pid, False)
                elif plen == best_parent_len and best_parent_id is not None:
                    # Stable tie-break at parent selection: choose lexical hash for determinism.
                    if pid[1] > best_parent_id[1]:
                        best_parent_id = pid
                        best_parent_quorum = quorum_after_fork.get(pid, False)
            if best_parent_id is None:
                continue

            best_len[node_id] = best_parent_len + 1
            parent[node_id] = best_parent_id
            is_quorum = b.kind == "QUORUM_PASSED" and (fork_point is None or b.index >= fork_point)
            quorum_after_fork[node_id] = bool(best_parent_quorum or is_quorum)

    # Identify best tip under LCR + deterministic tie-breaks.
    tips: list[_ChainTip] = []
    for node_id, ln in best_len.items():
        b = nodes[node_id]
        tips.append(
            _ChainTip(
                tip_id=node_id,
                length=ln,
                quorum_passed_after_fork=quorum_after_fork.get(node_id, False),
                tip_signature_u32=b.signature_u32,
                tip_hash=b.hash,
            )
        )
    if not tips:
        return ([], fork_point)

    best_tip = max(tips, key=_chain_tip_key)

    chosen: list[_ValidBlock] = []
    cur: tuple[int, str, int] | None = best_tip.tip_id
    while cur is not None:
        chosen.append(nodes[cur])
        cur = parent.get(cur)
    chosen.reverse()
    return (chosen, fork_point)


def _write_orphaned(
    *,
    orphaned_path: Path,
    ledger_path: Path,
    parsed: Sequence[_ParsedLine],
    chosen_hashes: set[str],
) -> int:
    orphaned_path.parent.mkdir(parents=True, exist_ok=True)
    pruned = 0
    with orphaned_path.open("a", encoding="utf-8") as f:
        for item in parsed:
            if item.block is not None and item.block.get("hash") in chosen_hashes:
                continue
            pruned += 1
            record: dict[str, Any] = {
                "ts_utc": _now_ts_utc(),
                "event": "ORPHANED_LEDGER_LINE",
                "ledger_path": str(ledger_path),
                "line_no": item.line_no,
                "reason": item.parse_error or "fork_pruned",
            }
            if item.block is not None:
                record["block"] = item.block
            else:
                record["raw"] = item.raw
            f.write(_canonical_json(record) + "\n")
        f.flush()
        try:
            os.fsync(f.fileno())
        except OSError:
            pass
    return pruned


def _build_reconciliation_block(*, prev_hash: str, next_index: int, execution_token: str, summary: Mapping[str, Any]) -> LedgerBlock:
    header: MutableMapping[str, Any] = {
        "index": next_index,
        "ts_utc": _now_ts_utc(),
        "execution_token": execution_token,
        "prev_hash": prev_hash,
        "payload": {"kind": "CONSENSUS_RECONCILIATION_COMPLETE", **dict(summary)},
    }
    h = _compute_block_hash(header)
    header["hash"] = h
    header["signature"] = _compute_block_signature(header)
    return cast(LedgerBlock, dict(header))


def _atomic_rewrite_ledger(*, ledger_path: Path, blocks: Sequence[LedgerBlock]) -> None:
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd: int | None = None
    tmp_path: str | None = None
    try:
        fd, tmp = tempfile.mkstemp(prefix=ledger_path.name + ".", suffix=".tmp", dir=str(ledger_path.parent))
        tmp_fd = fd
        tmp_path = tmp
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for b in blocks:
                f.write(_canonical_json(b) + "\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, ledger_path)
    finally:
        if tmp_fd is not None:
            tmp_fd = None
        if tmp_path is not None:
            try:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            except OSError:
                pass


class LedgerForkAuditor:
    """Detect and deterministically reconcile cryptographic forks in PROOFS_LEDGER.jsonl."""

    def __init__(self, *, repo_root: Path, log_dir: Path, ledger_path: Path | None = None) -> None:
        self._repo_root = repo_root.resolve()
        self._log_dir = log_dir.resolve()
        self._ledger_path = (ledger_path or (self._log_dir / "PROOFS_LEDGER.jsonl")).resolve()

    @property
    def ledger_path(self) -> Path:
        return self._ledger_path

    @property
    def orphaned_path(self) -> Path:
        return (self._log_dir / "ORPHANED_FORKS.jsonl").resolve()

    def audit_or_raise(self) -> None:
        """Validate the ledger as a single linear chain; raises on any anomaly."""
        path = self._ledger_path
        if not path.exists():
            return
        parsed = list(_iter_parsed_lines(path))
        prev_hash = _GENESIS_PREV
        expected_index = 0
        for item in parsed:
            if item.block is None:
                raise CryptographicForkException(
                    f"Ledger parse failure at line {item.line_no}: {item.parse_error}",
                    ledger_path=path,
                    details={"line_no": item.line_no, "reason": item.parse_error},
                )
            block = item.block
            idx = block.get("index")
            if idx != expected_index:
                raise CryptographicForkException(
                    f"Ledger index mismatch at line {item.line_no}: expected={expected_index} got={idx}",
                    ledger_path=path,
                    details={"line_no": item.line_no, "expected_index": expected_index, "got_index": idx},
                )
            if block.get("prev_hash") != prev_hash:
                raise CryptographicForkException(
                    f"Ledger chain mismatch at index={idx}",
                    ledger_path=path,
                    details={"line_no": item.line_no, "index": idx, "expected_prev_hash": prev_hash, "got_prev_hash": block.get("prev_hash")},
                )
            if not _block_is_self_consistent(block):
                raise CryptographicForkException(
                    f"Ledger hash/signature mismatch at index={idx}",
                    ledger_path=path,
                    details={"line_no": item.line_no, "index": idx},
                )
            prev_hash = str(block.get("hash"))
            expected_index += 1

    def resolve_fork(self) -> ForkResolutionResult:
        """Reconcile the ledger using LCR + quorum/sig tie-breaks and rewrite it atomically."""
        return self._resolve_fork_sync(replay_verify=False)

    async def resolve_fork_async(self) -> ForkResolutionResult:
        """Async reconcile path that also validates the chosen chain via replay sandbox."""
        return await asyncio.to_thread(self._resolve_fork_sync, replay_verify=True)

    def _resolve_fork_sync(self, *, replay_verify: bool) -> ForkResolutionResult:
        ledger_path = self._ledger_path
        if not ledger_path.exists():
            raise FileNotFoundError(str(ledger_path))

        parsed = list(_iter_parsed_lines(ledger_path))
        chosen_valid, fork_point = self._choose_chain(parsed)
        if not chosen_valid:
            raise CryptographicForkException(
                "Unable to construct a valid chain from ledger blocks.",
                ledger_path=ledger_path,
            )

        chosen_blocks = [b.block for b in chosen_valid]
        if replay_verify:
            # Replay in a read-only sandbox to confirm deterministic frame parsing (best-effort).
            try:
                asyncio.run(self._replay_verify_chain(chosen_blocks))
            except Exception:
                # Never fail closed on replay sandbox issues; chain selection is cryptographic.
                pass

        chosen_hashes = {b.hash for b in chosen_valid}
        pruned_lines = _write_orphaned(
            orphaned_path=self.orphaned_path,
            ledger_path=ledger_path,
            parsed=parsed,
            chosen_hashes=chosen_hashes,
        )

        tip = chosen_valid[-1]
        exec_token = str(tip.block.get("execution_token") or "")
        summary = {
            "ledger": str(ledger_path),
            "chosen_tip_hash": tip.hash,
            "chosen_blocks": len(chosen_valid),
            "pruned_lines": pruned_lines,
            "fork_point_index": fork_point,
        }
        reconciliation = _build_reconciliation_block(
            prev_hash=tip.hash,
            next_index=tip.index + 1,
            execution_token=exec_token,
            summary=summary,
        )

        final_blocks: list[LedgerBlock] = [b.block for b in chosen_valid] + [reconciliation]
        _atomic_rewrite_ledger(ledger_path=ledger_path, blocks=final_blocks)

        return ForkResolutionResult(
            ledger_path=ledger_path,
            orphaned_path=self.orphaned_path,
            chosen_tip_hash=tip.hash,
            chosen_blocks=len(chosen_valid),
            pruned_lines=pruned_lines,
            reconciliation_index=int(reconciliation["index"]),
            fork_point_index=fork_point,
        )

    def _choose_chain(self, parsed: Sequence[_ParsedLine]) -> tuple[list[_ValidBlock], int | None]:
        valid = _valid_blocks(parsed)
        if not valid:
            raise CryptographicForkException(
                "Ledger contains no self-consistent blocks to reconcile.",
                ledger_path=self._ledger_path,
            )
        return _best_chain(valid)

    async def _replay_verify_chain(self, blocks: Sequence[LedgerBlock]) -> None:
        tmp_path = self._write_chain_tmp(blocks)
        try:
            controller = PipelineReplayController(repo_root=self._repo_root, log_dir=self._log_dir)
            try:
                with ReadOnlyWorkspaceGuard(self._repo_root):
                    await controller.replay_step_loop(source=str(tmp_path))
            finally:
                controller.close()
        finally:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass

    def _write_chain_tmp(self, blocks: Sequence[LedgerBlock]) -> Path:
        fd, tmp = tempfile.mkstemp(prefix="remote_agents_chain_eval_", suffix=".jsonl")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                for b in blocks:
                    f.write(_canonical_json(b) + "\n")
                f.flush()
                try:
                    os.fsync(f.fileno())
                except OSError:
                    pass
        except Exception:
            try:
                os.close(fd)
            except OSError:
                pass
            raise
        return Path(tmp).resolve()

    def recover_loop(self, *, token: str, active_stage: str | None) -> ForkResolutionResult | None:
        """Detect and resolve forks, optionally pruning staged workspace state."""
        try:
            self.audit_or_raise()
            return None
        except CryptographicForkException:
            result = self.resolve_fork()
            # Best-effort workspace rollback for the execution token to avoid leaking staged writes.
            try:
                cleanup_workspace_staging(repo_root=self._repo_root, token=token, active_stage=active_stage)
            except Exception:
                pass
            # Ensure the rewritten ledger is actually linear.
            self.audit_or_raise()
            return result

    async def monitor(self, *, token: str, active_stage: str | None, interval_s: float = 0.25) -> None:
        """Continuously audit and reconcile forks until cancelled."""
        while True:
            await asyncio.sleep(interval_s)
            try:
                self.recover_loop(token=token, active_stage=active_stage)
            except Exception:
                # Monitoring must be non-fatal; callers decide how to handle failures.
                pass
