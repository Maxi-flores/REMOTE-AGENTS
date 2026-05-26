"""Crash-consistent workspace transaction manager (stdlib-only, Python 3.10+).

This module provides a copy-on-write transaction layer for repository workspace
side-effects. Write operations performed within an active transaction are
redirected into a hidden staging directory (``.workspace_staging/``) and only
made visible in the live workspace after an explicit commit.

Isolation is enforced at read-committed level via a non-blocking lock registry.
When available, advisory file locks (fcntl) are additionally used to prevent
cross-process interference.
"""

from __future__ import annotations

import builtins
import base64
import contextvars
import hashlib
import json
import os
import shutil
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Any, Iterable, Literal, Mapping, MutableMapping, Sequence

from core.proof_ledger import ProofLedgerManager

try:  # pragma: no cover - platform-dependent
    import fcntl  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    fcntl = None  # type: ignore[assignment]

_STAGING_DIRNAME = ".workspace_staging"
_LOCKS_DIRNAME = ".locks"
_MANIFEST_FILENAME = "manifest.json"


class WorkspaceIsolationError(RuntimeError):
    """Raised when a non-blocking read/write lock cannot be acquired."""


class WorkspaceTransactionError(RuntimeError):
    """Raised when the transaction manager detects an unrecoverable inconsistency."""


def _atomic_write_json(path: Path, obj: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    tmp = path.with_name(path.name + f".{uuid.uuid4().hex}.tmp")
    try:
        tmp.write_text(data, encoding="utf-8")
        os.replace(tmp, path)
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


@dataclass(frozen=True, slots=True)
class _TouchedEntry:
    op: Literal["write", "delete"]
    root_index: int
    relpath: str

    def key(self) -> tuple[str, int, str]:
        return (self.op, self.root_index, self.relpath)


class _LockRegistry:
    def __init__(self) -> None:
        self._mu = threading.Lock()
        self._owners: dict[str, str] = {}

    def try_acquire(self, abs_path: str, *, owner: str) -> None:
        with self._mu:
            current = self._owners.get(abs_path)
            if current is None or current == owner:
                self._owners[abs_path] = owner
                return
            raise WorkspaceIsolationError(f"Path locked by another transaction: {abs_path}")

    def release_all(self, *, owner: str) -> None:
        with self._mu:
            to_delete = [p for p, o in self._owners.items() if o == owner]
            for p in to_delete:
                self._owners.pop(p, None)

    def is_locked_by_other(self, abs_path: str, *, owner: str | None) -> bool:
        with self._mu:
            current = self._owners.get(abs_path)
            if current is None:
                return False
            if owner is not None and current == owner:
                return False
            return True


_LOCKS = _LockRegistry()
_CURRENT_TX: contextvars.ContextVar["WorkspaceTransaction | None"] = contextvars.ContextVar(
    "workspace_transaction",
    default=None,
)

_HOOKS_INSTALLED = False
_REAL_OPEN = builtins.open
_REAL_PATH_OPEN = Path.open
_REAL_PATH_UNLINK = Path.unlink


def current_transaction() -> "WorkspaceTransaction | None":
    return _CURRENT_TX.get()


def ensure_workspace_io_hooks_installed() -> None:
    """Install process-wide IO hooks once (idempotent)."""
    global _HOOKS_INSTALLED
    if _HOOKS_INSTALLED:
        return

    def _path_open_hook(path_obj: Path, mode: str = "r", *args: Any, **kwargs: Any) -> IO[Any]:
        tx = _CURRENT_TX.get()
        if tx is None:
            return _REAL_PATH_OPEN(path_obj, mode, *args, **kwargs)
        mapped = tx._map_for_open(path_obj, mode=mode)
        return _REAL_PATH_OPEN(mapped, mode, *args, **kwargs)

    def _builtins_open_hook(file: Any, mode: str = "r", *args: Any, **kwargs: Any) -> IO[Any]:
        # Preserve builtins.open behavior for file descriptors.
        if isinstance(file, int):
            return _REAL_OPEN(file, mode, *args, **kwargs)
        tx = _CURRENT_TX.get()
        if tx is None:
            return _REAL_OPEN(file, mode, *args, **kwargs)
        mapped = tx._map_for_open(file, mode=mode)
        return _REAL_OPEN(mapped, mode, *args, **kwargs)

    def _path_unlink_hook(path_obj: Path, *args: Any, **kwargs: Any) -> None:
        tx = _CURRENT_TX.get()
        if tx is None:
            return _REAL_PATH_UNLINK(path_obj, *args, **kwargs)
        tx.stage_delete(path_obj)
        return None

    Path.open = _path_open_hook  # type: ignore[assignment]
    builtins.open = _builtins_open_hook  # type: ignore[assignment]
    Path.unlink = _path_unlink_hook  # type: ignore[assignment]
    _HOOKS_INSTALLED = True


def _mode_is_write(mode: str) -> bool:
    # Any of these implies a write or mutation.
    return any(flag in mode for flag in ("w", "a", "x", "+"))


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _stable_lock_name(abs_path: str) -> str:
    digest = hashlib.sha256(abs_path.encode("utf-8")).hexdigest()
    return digest[:32]


class WorkspaceTransaction:
    """Copy-on-write workspace transaction with staged writes and deterministic cleanup."""

    def __init__(
        self,
        *,
        repo_roots: Sequence[Path],
        token: str,
        stage: str,
        exclude_roots: Sequence[Path] | None = None,
        proof_ledger: ProofLedgerManager | None = None,
    ) -> None:
        if not repo_roots:
            raise ValueError("repo_roots must be non-empty")
        self._repo_roots = [p.resolve() for p in repo_roots]
        self._exclude_roots = [p.resolve() for p in (exclude_roots or [])]
        self._token = token
        self._stage = stage
        self._proof_ledger = proof_ledger
        self._txn_id = uuid.uuid4().hex
        self._touched: MutableMapping[tuple[str, int, str], _TouchedEntry] = {}
        self._lock_fds: dict[str, int] = {}
        self._ctx_token: contextvars.Token["WorkspaceTransaction | None"] | None = None
        self._finalized = False

        # Single staging base rooted at the first repo root.
        self._staging_base = self._repo_roots[0] / _STAGING_DIRNAME / self._token / self._stage / self._txn_id
        self._locks_dir = self._repo_roots[0] / _STAGING_DIRNAME / _LOCKS_DIRNAME
        self._manifest_path = self._staging_base / _MANIFEST_FILENAME

    @property
    def token(self) -> str:
        return self._token

    @property
    def stage(self) -> str:
        return self._stage

    def __enter__(self) -> "WorkspaceTransaction":
        ensure_workspace_io_hooks_installed()
        self._ctx_token = _CURRENT_TX.set(self)
        self._staging_base.mkdir(parents=True, exist_ok=True)
        self._locks_dir.mkdir(parents=True, exist_ok=True)
        self._write_manifest(state="staging")
        ledger = self._proof_ledger
        if ledger is not None:
            try:
                ledger.append_block(
                    {
                        "kind": "TX_BEGIN",
                        "token": self._token,
                        "stage": self._stage,
                        "txn_id": self._txn_id,
                        "staging_base": str(self._staging_base),
                        "repo_roots": [str(p) for p in self._repo_roots],
                    }
                )
            except Exception:
                pass
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:  # type: ignore[no-untyped-def]
        try:
            if exc is not None and not self._finalized:
                self.rollback()
        finally:
            self._release_locks()
            self._reset_context()
        return False

    async def __aenter__(self) -> "WorkspaceTransaction":
        return self.__enter__()

    async def __aexit__(self, exc_type, exc, tb) -> bool:  # type: ignore[no-untyped-def]
        return self.__exit__(exc_type, exc, tb)

    def _reset_context(self) -> None:
        if self._ctx_token is not None:
            _CURRENT_TX.reset(self._ctx_token)
            self._ctx_token = None

    def _write_manifest(self, *, state: Literal["staging", "committing", "committed", "rolled_back"]) -> None:
        manifest = {
            "version": 1,
            "token": self._token,
            "stage": self._stage,
            "txn_id": self._txn_id,
            "state": state,
            "created_at": time.time(),
            "repo_roots": [str(p) for p in self._repo_roots],
            "touched": [
                {"op": e.op, "root_index": e.root_index, "relpath": e.relpath}
                for e in sorted(self._touched.values(), key=lambda x: (x.op, x.root_index, x.relpath))
            ],
        }
        _atomic_write_json(self._manifest_path, manifest)

    def _is_excluded(self, abs_path: Path) -> bool:
        for ex in self._exclude_roots:
            if _is_within(abs_path, ex):
                return True
        # Never intercept staging or VCS internals rooted under protected roots.
        for root in self._repo_roots:
            if _is_within(abs_path, root / _STAGING_DIRNAME) or _is_within(abs_path, root / ".git"):
                return True
        return False

    def _find_root_index(self, abs_path: Path) -> int | None:
        best: tuple[int, int] | None = None  # (len, idx)
        for idx, root in enumerate(self._repo_roots):
            if _is_within(abs_path, root):
                score = len(str(root))
                if best is None or score > best[0]:
                    best = (score, idx)
        return best[1] if best is not None else None

    def _stage_path(self, *, root_index: int, relpath: str) -> Path:
        return self._staging_base / str(root_index) / relpath

    def _acquire_lock(self, abs_path: Path) -> None:
        abs_str = str(abs_path)
        _LOCKS.try_acquire(abs_str, owner=self._txn_id)
        if fcntl is None:
            return
        lock_name = _stable_lock_name(abs_str)
        lock_path = self._locks_dir / lock_name
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        except OSError:
            return
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except Exception:
            try:
                os.close(fd)
            except OSError:
                pass
            raise WorkspaceIsolationError(f"Unable to acquire filesystem lock: {abs_str}")
        self._lock_fds[lock_name] = fd

    def _release_locks(self) -> None:
        _LOCKS.release_all(owner=self._txn_id)
        for _name, fd in list(self._lock_fds.items()):
            try:
                if fcntl is not None:
                    try:
                        fcntl.flock(fd, fcntl.LOCK_UN)
                    except Exception:
                        pass
                os.close(fd)
            except OSError:
                pass
        self._lock_fds.clear()

    def _register_touch(self, entry: _TouchedEntry) -> None:
        self._touched[entry.key()] = entry
        self._write_manifest(state="staging")

    def _map_for_open(self, file: Any, *, mode: str) -> Any:
        # Preserve behavior for non-path-like objects.
        try:
            path = Path(file)
        except TypeError:
            return file

        abs_path = path if path.is_absolute() else (Path.cwd() / path)
        abs_path = abs_path.resolve()
        if self._is_excluded(abs_path):
            return file

        root_index = self._find_root_index(abs_path)
        if root_index is None:
            return file

        # Enforce read-committed isolation.
        if not _mode_is_write(mode):
            if _LOCKS.is_locked_by_other(str(abs_path), owner=self._txn_id):
                raise WorkspaceIsolationError(f"Read blocked by uncommitted writer: {abs_path}")
            relpath = abs_path.relative_to(self._repo_roots[root_index]).as_posix()
            staged = self._stage_path(root_index=root_index, relpath=relpath)
            if staged.exists():
                return staged
            return file

        # Writes go to staging.
        self._acquire_lock(abs_path)
        relpath = abs_path.relative_to(self._repo_roots[root_index]).as_posix()
        staged = self._stage_path(root_index=root_index, relpath=relpath)
        staged.parent.mkdir(parents=True, exist_ok=True)

        # Exclusive create should respect the live path too.
        if "x" in mode and not staged.exists() and abs_path.exists():
            raise FileExistsError(str(abs_path))

        # Appends should start from the committed version.
        if "a" in mode and not staged.exists() and abs_path.exists():
            try:
                shutil.copy2(abs_path, staged)
            except OSError:
                pass

        self._register_touch(_TouchedEntry(op="write", root_index=root_index, relpath=relpath))
        return staged

    def stage_delete(self, path: Path) -> None:
        abs_path = path if path.is_absolute() else (Path.cwd() / path)
        abs_path = abs_path.resolve()
        if self._is_excluded(abs_path):
            return
        root_index = self._find_root_index(abs_path)
        if root_index is None:
            return
        self._acquire_lock(abs_path)
        relpath = abs_path.relative_to(self._repo_roots[root_index]).as_posix()
        self._register_touch(_TouchedEntry(op="delete", root_index=root_index, relpath=relpath))

    def commit(self) -> None:
        if self._finalized:
            return
        ledger = self._proof_ledger
        snapshot = self._collect_staged_snapshot()
        self._write_manifest(state="committing")
        for entry in list(self._touched.values()):
            root = self._repo_roots[entry.root_index]
            live = root / entry.relpath
            if entry.op == "delete":
                try:
                    if live.exists():
                        live.unlink()
                except OSError:
                    pass
                continue
            staged = self._stage_path(root_index=entry.root_index, relpath=entry.relpath)
            if not staged.exists():
                continue
            try:
                live.parent.mkdir(parents=True, exist_ok=True)
            except OSError:
                pass
            try:
                os.replace(staged, live)
            except OSError as exc:
                raise WorkspaceTransactionError(f"Commit failed for {live}: {exc}") from exc
        self._write_manifest(state="committed")
        self._finalized = True
        if ledger is not None:
            try:
                ledger.append_block(
                    {
                        "kind": "TX_COMMIT",
                        "token": self._token,
                        "stage": self._stage,
                        "txn_id": self._txn_id,
                        "touched": snapshot.get("touched", []),
                        "staged_files": snapshot.get("staged_files", {}),
                    }
                )
            except Exception:
                pass
        self._cleanup_staging()

    def rollback(self) -> None:
        if self._finalized:
            return
        ledger = self._proof_ledger
        snapshot = self._collect_staged_snapshot()
        self._write_manifest(state="rolled_back")
        self._finalized = True
        if ledger is not None:
            try:
                ledger.append_block(
                    {
                        "kind": "TX_ROLLBACK",
                        "token": self._token,
                        "stage": self._stage,
                        "txn_id": self._txn_id,
                        "touched": snapshot.get("touched", []),
                        "staged_files": snapshot.get("staged_files", {}),
                    }
                )
            except Exception:
                pass
        self._cleanup_staging()

    def _collect_staged_snapshot(self) -> Mapping[str, Any]:
        """Collect a bounded snapshot of staged file content for forensic replay."""
        touched = [
            {"op": e.op, "root_index": e.root_index, "relpath": e.relpath}
            for e in sorted(self._touched.values(), key=lambda x: (x.op, x.root_index, x.relpath))
        ]
        staged_files: dict[str, Any] = {}
        for entry in sorted(self._touched.values(), key=lambda x: (x.root_index, x.relpath, x.op)):
            if entry.op != "write":
                continue
            staged = self._stage_path(root_index=entry.root_index, relpath=entry.relpath)
            if not staged.exists() or not staged.is_file():
                continue
            try:
                data = staged.read_bytes()
            except OSError:
                continue
            sha = hashlib.sha256(data).hexdigest()
            item: dict[str, Any] = {"sha256": sha, "bytes": len(data)}
            if len(data) <= 65536:
                item["content_b64"] = base64.b64encode(data).decode("ascii")
            staged_files[f"{entry.root_index}:{entry.relpath}"] = item
        return {"touched": touched, "staged_files": staged_files}

    def _cleanup_staging(self) -> None:
        try:
            if self._staging_base.exists():
                shutil.rmtree(self._staging_base, ignore_errors=True)
        finally:
            # Best-effort prune empty parents up to token root.
            token_root = self._repo_roots[0] / _STAGING_DIRNAME / self._token
            for p in (token_root / self._stage, token_root, self._repo_roots[0] / _STAGING_DIRNAME):
                try:
                    if p.exists() and p.is_dir() and not any(p.iterdir()):
                        p.rmdir()
                except OSError:
                    pass

    @staticmethod
    def recover_commit_from_manifest(manifest_path: Path) -> None:
        raw = json.loads(manifest_path.read_text(encoding="utf-8", errors="replace"))
        if not isinstance(raw, dict):
            return
        repo_roots = raw.get("repo_roots")
        touched = raw.get("touched")
        if not isinstance(repo_roots, list) or not all(isinstance(x, str) for x in repo_roots):
            return
        if not isinstance(touched, list):
            return
        roots = [Path(x).resolve() for x in repo_roots]
        txn_dir = manifest_path.parent
        for item in touched:
            if not isinstance(item, dict):
                continue
            op = item.get("op")
            root_index = item.get("root_index")
            relpath = item.get("relpath")
            if op not in ("write", "delete") or not isinstance(root_index, int) or not isinstance(relpath, str):
                continue
            if root_index < 0 or root_index >= len(roots):
                continue
            live = roots[root_index] / relpath
            if op == "delete":
                try:
                    if live.exists():
                        live.unlink()
                except OSError:
                    pass
                continue
            staged = txn_dir / str(root_index) / relpath
            if not staged.exists():
                continue
            try:
                live.parent.mkdir(parents=True, exist_ok=True)
            except OSError:
                pass
            try:
                os.replace(staged, live)
            except OSError:
                pass


_STAGE_RANK: dict[str, int] = {
    "intake_to_architecture": 0,
    "architecture_to_risk": 1,
    "risk_to_build_execution": 2,
}


def cleanup_workspace_staging(
    *,
    repo_root: Path,
    token: str,
    active_stage: str | None,
) -> None:
    """Clean or finalize orphaned staging for a given execution token."""
    base = repo_root.resolve() / _STAGING_DIRNAME / token
    if not base.exists():
        return

    if active_stage is None:
        shutil.rmtree(base, ignore_errors=True)
        return

    active_rank = _STAGE_RANK.get(active_stage, -1)
    try:
        stage_dirs = [p for p in base.iterdir() if p.is_dir()]
    except OSError:
        return

    for stage_dir in stage_dirs:
        stage_rank = _STAGE_RANK.get(stage_dir.name, 999)
        if stage_rank > active_rank:
            shutil.rmtree(stage_dir, ignore_errors=True)
            continue
        try:
            txn_dirs = [p for p in stage_dir.iterdir() if p.is_dir()]
        except OSError:
            continue
        for txn_dir in txn_dirs:
            manifest = txn_dir / _MANIFEST_FILENAME
            if not manifest.exists():
                shutil.rmtree(txn_dir, ignore_errors=True)
                continue
            # For any stage <= active_stage, ensure staged writes are applied.
            try:
                WorkspaceTransaction.recover_commit_from_manifest(manifest)
            except Exception:
                pass
            shutil.rmtree(txn_dir, ignore_errors=True)

    # Best-effort prune.
    try:
        if base.exists() and not any(base.iterdir()):
            base.rmdir()
    except OSError:
        pass
