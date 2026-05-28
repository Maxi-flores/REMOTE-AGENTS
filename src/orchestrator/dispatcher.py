"""Outbound callback dispatcher (stdlib-only).

Persists completion envelopes to disk and retries delivery with exponential
backoff so a temporary platform outage doesn't lose task results.
"""

from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


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

