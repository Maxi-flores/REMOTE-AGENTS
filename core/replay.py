"""Deterministic time-travel replay controller (stdlib-only, Python 3.10+).

Replay consumes a previously captured `logs/PROOFS_LEDGER.jsonl` (or a
`logs/QUORUM_DISSENT_SNAPSHOT.json`) and reconstructs a side-effect-free view of
the pipeline history. It is intended for offline forensic debugging and
independent verification of integrity via the ledger hash chain + signatures.
"""

from __future__ import annotations

import base64
import builtins
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable, Iterator, Mapping, MutableMapping

from core.proof_ledger import ProofLedgerBlock, iter_ledger_blocks, verify_ledger_blocks


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _mode_is_write(mode: str) -> bool:
    return any(flag in mode for flag in ("w", "a", "x", "+"))


class ReadOnlyWorkspaceGuard:
    """Best-effort guardrail to prevent writes into a live repo during replay."""

    def __init__(self, repo_root: Path) -> None:
        self._repo_root = repo_root.resolve()
        self._orig_open = builtins.open
        self._orig_path_open = Path.open
        self._orig_unlink = Path.unlink

    def __enter__(self) -> "ReadOnlyWorkspaceGuard":
        repo_root = self._repo_root

        def _open(file: Any, mode: str = "r", *args: Any, **kwargs: Any):  # type: ignore[no-untyped-def]
            if isinstance(file, int):
                return self._orig_open(file, mode, *args, **kwargs)
            try:
                p = Path(file)
            except TypeError:
                return self._orig_open(file, mode, *args, **kwargs)
            if _mode_is_write(mode) and _is_within(p, repo_root):
                raise PermissionError(f"Replay sandbox forbids write under repo root: {p}")
            return self._orig_open(file, mode, *args, **kwargs)

        def _path_open(path_obj: Path, mode: str = "r", *args: Any, **kwargs: Any):  # type: ignore[no-untyped-def]
            if _mode_is_write(mode) and _is_within(path_obj, repo_root):
                raise PermissionError(f"Replay sandbox forbids write under repo root: {path_obj}")
            return self._orig_path_open(path_obj, mode, *args, **kwargs)

        def _unlink(path_obj: Path, *args: Any, **kwargs: Any):  # type: ignore[no-untyped-def]
            if _is_within(path_obj, repo_root):
                raise PermissionError(f"Replay sandbox forbids unlink under repo root: {path_obj}")
            return self._orig_unlink(path_obj, *args, **kwargs)

        builtins.open = _open  # type: ignore[assignment]
        Path.open = _path_open  # type: ignore[assignment]
        Path.unlink = _unlink  # type: ignore[assignment]
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:  # type: ignore[no-untyped-def]
        builtins.open = self._orig_open  # type: ignore[assignment]
        Path.open = self._orig_path_open  # type: ignore[assignment]
        Path.unlink = self._orig_unlink  # type: ignore[assignment]
        return False


@dataclass(frozen=True, slots=True)
class ReplayFrame:
    ledger_index: int
    frame_kind: str
    payload: Mapping[str, Any]
    staging_snapshot: Path | None


@dataclass(frozen=True, slots=True)
class ReplayResult:
    frames: list[str]
    verified_blocks: int
    sandbox_root: Path


class PipelineReplayController:
    """Replay controller driven by the immutable proof ledger."""

    def __init__(self, *, repo_root: Path, log_dir: Path) -> None:
        self._repo_root = repo_root.resolve()
        self._log_dir = log_dir.resolve()
        self._sandbox_tmp: tempfile.TemporaryDirectory[str] | None = None
        self._sandbox_root: Path | None = None

    @property
    def sandbox_root(self) -> Path:
        if self._sandbox_root is None:
            raise RuntimeError("Replay sandbox not initialized")
        return self._sandbox_root

    def _load_verified_blocks(self, source: str) -> list[ProofLedgerBlock]:
        source = source.strip()
        if source.isdigit():
            ledger_path = self._log_dir / "PROOFS_LEDGER.jsonl"
            blocks = verify_ledger_blocks(iter_ledger_blocks(ledger_path))
            start = int(source)
            if start < 0 or start > len(blocks):
                raise ValueError(f"Replay start index out of range: {start}")
            return blocks[start:]

        path = Path(source)
        if not path.is_absolute():
            path = (self._log_dir / source).resolve()
        if not path.exists():
            raise FileNotFoundError(str(path))
        if path.name.endswith(".jsonl"):
            return verify_ledger_blocks(iter_ledger_blocks(path))
        # Snapshot JSON fallback.
        raw = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        if not isinstance(raw, dict):
            raise ValueError("Snapshot must be a JSON object.")
        pseudo: ProofLedgerBlock = {
            "index": 0,
            "ts_utc": "snapshot",
            "execution_token": str(raw.get("execution_token") or "snapshot"),
            "prev_hash": "0" * 64,
            "payload": raw,
            "hash": "0" * 64,
            "signature": "00000000",
        }
        return [pseudo]

    def _ensure_sandbox(self) -> None:
        if self._sandbox_tmp is not None:
            return
        self._sandbox_tmp = tempfile.TemporaryDirectory(prefix="remote_agents_replay_")
        self._sandbox_root = Path(self._sandbox_tmp.name).resolve()

    def close(self) -> None:
        if self._sandbox_tmp is not None:
            self._sandbox_tmp.cleanup()
        self._sandbox_tmp = None
        self._sandbox_root = None

    def _frame_kind(self, payload: Mapping[str, Any]) -> str:
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

    def _apply_staged_files(
        self, *, token: str, stage: str, txn_id: str, staged_files: Mapping[str, Any]
    ) -> Path:
        self._ensure_sandbox()
        root = self.sandbox_root / ".workspace_staging" / token / stage / txn_id
        root.mkdir(parents=True, exist_ok=True)
        for key, meta in staged_files.items():
            if not isinstance(key, str) or not isinstance(meta, dict):
                continue
            # key format: "<root_index>:<relpath>"
            if ":" not in key:
                continue
            root_idx, rel = key.split(":", 1)
            try:
                root_idx_int = int(root_idx)
            except ValueError:
                continue
            content_b64 = meta.get("content_b64")
            if not isinstance(content_b64, str):
                continue
            try:
                data = base64.b64decode(content_b64.encode("ascii"), validate=True)
            except Exception:
                continue
            out = root / str(root_idx_int) / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(data)
        return root

    async def replay_step_loop(
        self,
        *,
        source: str,
        on_step: Callable[[ReplayFrame], Awaitable[None]] | None = None,
    ) -> ReplayResult:
        blocks = self._load_verified_blocks(source)
        self._ensure_sandbox()

        frames: list[str] = []
        for block in blocks:
            payload_obj = block.get("payload")
            if not isinstance(payload_obj, dict):
                continue
            payload: Mapping[str, Any] = payload_obj
            kind = self._frame_kind(payload)
            frames.append(kind)

            staging_snapshot: Path | None = None
            if kind in ("TX_COMMIT", "TX_ROLLBACK"):
                token = str(payload.get("token") or "")
                stage = str(payload.get("stage") or "")
                txn_id = str(payload.get("txn_id") or "")
                staged_files = payload.get("staged_files")
                if token and stage and txn_id and isinstance(staged_files, dict):
                    staging_snapshot = self._apply_staged_files(
                        token=token, stage=stage, txn_id=txn_id, staged_files=staged_files
                    )

            frame = ReplayFrame(
                ledger_index=int(block.get("index", 0)),
                frame_kind=kind,
                payload=payload,
                staging_snapshot=staging_snapshot,
            )
            if on_step is not None:
                await on_step(frame)

        return ReplayResult(frames=frames, verified_blocks=len(blocks), sandbox_root=self.sandbox_root)

