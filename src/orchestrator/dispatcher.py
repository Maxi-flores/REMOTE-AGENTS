"""Dispatcher utilities (stdlib-only).

Persists completion envelopes to disk and retries delivery with exponential
backoff so a temporary platform outage doesn't lose task results.

Also provides a small CLI to enqueue manual tasks into `.platform_queue/`
without crafting raw JSON.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import sys
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


PLATFORM_QUEUE_DIR = Path(".platform_queue")
PLATFORM_TASK_FILE = PLATFORM_QUEUE_DIR / "next_task.json"
PLATFORM_LOCK_FILE = PLATFORM_QUEUE_DIR / "processing.lock"


def build_delivery_envelope(
    *,
    task_id: str,
    status: str,
    duration_seconds: float,
    execution_summary: str,
    artifacts_created: Iterable[str],
) -> dict[str, Any]:
    return {
        "task_id": str(task_id),
        "status": str(status),
        "duration_seconds": float(duration_seconds),
        "execution_summary": str(execution_summary or ""),
        "artifacts_created": [str(p) for p in artifacts_created],
    }


@dataclass(slots=True)
class DispatcherConfig:
    callback_url: str
    bearer_token: str | None = None
    outbox_dir: Path = Path(".platform_queue/outbound")
    poll_interval_s: float = 0.25
    request_timeout_s: float = 10.0
    max_backoff_s: float = 60.0


class OutboundCallbackDispatcher:
    """Background worker that delivers persisted envelopes to a platform endpoint."""

    def __init__(self, config: DispatcherConfig):
        self._cfg = config
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._attempts: dict[str, int] = {}
        self._next_attempt_at: dict[str, float] = {}

    def start(self) -> None:
        self._cfg.outbox_dir.mkdir(parents=True, exist_ok=True)
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="platform:dispatcher", daemon=True)
        self._thread.start()

    def stop(self, *, timeout_s: float = 2.0) -> None:
        self._stop.set()
        if self._thread is None:
            return
        self._thread.join(timeout=float(timeout_s))

    def enqueue(self, envelope: dict[str, Any]) -> Path:
        self._cfg.outbox_dir.mkdir(parents=True, exist_ok=True)
        task_id = str(envelope.get("task_id") or "unknown")
        safe_task_id = "".join(ch if (ch.isalnum() or ch in ("-", "_")) else "_" for ch in task_id)[:64]
        stamp = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
        nonce = f"{os.getpid()}_{int(time.time() * 1000)}"
        path = self._cfg.outbox_dir / f"{stamp}__{safe_task_id}__{nonce}.json"
        tmp = self._cfg.outbox_dir / f".tmp.{path.name}"
        tmp.write_text(json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, path)
        return path

    def _run(self) -> None:
        while not self._stop.is_set():
            delivered_any = False
            for path in self._pending_files():
                if self._stop.is_set():
                    return
                now = time.monotonic()
                next_ts = self._next_attempt_at.get(str(path))
                if next_ts is not None and now < next_ts:
                    continue
                if self._try_deliver(path):
                    delivered_any = True
                else:
                    delivered_any = True
            if not delivered_any:
                self._stop.wait(float(self._cfg.poll_interval_s))

    def _pending_files(self) -> list[Path]:
        try:
            paths = [p for p in self._cfg.outbox_dir.glob("*.json") if p.is_file()]
        except OSError:
            return []
        paths.sort(key=lambda p: p.name)
        return paths

    def _try_deliver(self, path: Path) -> bool:
        key = str(path)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            self._post_json(payload)
        except Exception as exc:
            attempt = int(self._attempts.get(key, 0)) + 1
            self._attempts[key] = attempt
            backoff_s = min(float(self._cfg.max_backoff_s), float(2**min(attempt, 16)))
            self._next_attempt_at[key] = time.monotonic() + backoff_s
            return False

        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
        self._attempts.pop(key, None)
        self._next_attempt_at.pop(key, None)
        return True

    def _post_json(self, payload: dict[str, Any]) -> None:
        data = (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8", errors="strict")
        req = urllib.request.Request(
            url=str(self._cfg.callback_url),
            data=data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "REMOTE-AGENTS/dispatcher",
                **({"Authorization": f"Bearer {self._cfg.bearer_token}"} if self._cfg.bearer_token else {}),
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=float(self._cfg.request_timeout_s)) as resp:
            code = int(getattr(resp, "status", 200))
            if code < 200 or code >= 300:
                raise urllib.error.HTTPError(req.full_url, code, "non-2xx", resp.headers, None)


def _utc_ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _secure_task_id(*, repo: str, instruction: str, priority: int) -> str:
    seed = (
        f"{repo}\0{instruction}\0{priority}\0{time.time_ns()}\0{os.getpid()}\0{secrets.token_hex(16)}"
    ).encode("utf-8", errors="strict")
    return hashlib.sha256(seed).hexdigest()


def _atomic_exclusive_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8", errors="strict")

    fd: int | None = None
    try:
        fd = os.open(os.fspath(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        with os.fdopen(fd, "wb") as f:
            fd = None
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except Exception:
                pass


def enqueue_platform_task(*, repo: str, instruction: str, priority: int = 0) -> dict[str, Any]:
    """Create `next_task.json` atomically (O_EXCL) using the platform single-flight contract."""

    repo = str(repo or "").strip()
    instruction = str(instruction or "").strip()
    if not repo:
        raise ValueError("--repo is required")
    if not instruction:
        raise ValueError("--task is required")
    if not isinstance(priority, int) or isinstance(priority, bool):
        raise ValueError("--priority must be an integer")

    task_id = _secure_task_id(repo=repo, instruction=instruction, priority=int(priority))
    payload: dict[str, Any] = {
        "task_id": task_id,
        "instruction": instruction,
        "priority": int(priority),
        "target_repository": repo,
        "enqueued_utc": _utc_ts(),
        "source": "manual-dispatcher",
    }

    _atomic_exclusive_write(PLATFORM_TASK_FILE, payload)
    return payload


def flush_processing_locks() -> bool:
    """Remove `.platform_queue/processing.lock` if present."""

    try:
        PLATFORM_LOCK_FILE.unlink(missing_ok=True)
        return True
    except Exception:
        return False


def _build_cli_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="dispatcher.py",
        description="Manual task injector + stale-lock flush for the REMOTE-AGENTS platform queue.",
    )
    p.add_argument("--repo", help="Target repository name (e.g. ConceptSHOP).")
    p.add_argument("--task", help="Instruction text to enqueue.")
    p.add_argument("--priority", type=int, default=0, help="Higher runs first (default: 0).")
    p.add_argument(
        "--flush-locks",
        action="store_true",
        help="Delete `.platform_queue/processing.lock` (manual debugging escape hatch).",
    )
    return p


def _main(argv: list[str] | None = None) -> int:
    args = _build_cli_parser().parse_args(argv)

    if args.flush_locks:
        ok = flush_processing_locks()
        if ok:
            print(f"OK: pruned {PLATFORM_LOCK_FILE}")
            return 0
        print(f"ERROR: failed to prune {PLATFORM_LOCK_FILE}")
        return 2

    try:
        payload = enqueue_platform_task(repo=args.repo, instruction=args.task, priority=int(args.priority))
    except FileExistsError:
        print(f"ERROR: {PLATFORM_TASK_FILE} already exists (single-flight).")
        return 3
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 2

    print(f"OK: wrote {PLATFORM_TASK_FILE} (task_id={payload.get('task_id')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
