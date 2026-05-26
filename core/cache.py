"""Content-addressed, thread-safe cache for sandboxed agent stages (stdlib-only).

The autonomous office runtime can repeatedly run the same ISA->SAS->CRS->BOA
pipeline with identical inputs. This cache fingerprints each stage invocation
deterministically and stores the resulting JSON payload in a local object store.

On a cache hit, the AgentSandboxExecutor is bypassed entirely.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Any, Callable, Mapping, MutableMapping, Sequence

from core.telemetry import PipelineStage, TelemetryTracer

ManifestFingerprint = str


def _stable_json(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def _sha256_file(path: Path) -> str | None:
    try:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


@dataclass(frozen=True, slots=True)
class CacheTelemetry:
    wall_ms: float
    cpu_ms: float
    bytes_transferred: int
    sandbox_mode: str
    sandbox_trace: str


@dataclass(frozen=True, slots=True)
class CacheDecision:
    fingerprint: ManifestFingerprint
    cache_state: str  # "CACHE_HIT" | "CACHE_MISS"
    telemetry: CacheTelemetry


class WorkspaceCacheEngine:
    """Local content-addressed cache for stage JSON outputs.

    Thread-safe and asyncio-friendly: synchronous filesystem operations are
    executed via ``asyncio.to_thread``.
    """

    _STAGE_ORDER: tuple[PipelineStage, ...] = ("ISA", "SAS", "CRS", "BOA")

    def __init__(self, *, repo_root: Path, cache_root: Path | None = None) -> None:
        self._repo_root = repo_root.resolve()
        self._cache_root = (cache_root or (self._repo_root / ".workspace_cache")).resolve()
        self._objects_dir = self._cache_root / "objects"
        self._index_path = self._cache_root / "index.json"
        self._lock = RLock()

    def _object_path(self, fingerprint: ManifestFingerprint) -> Path:
        return self._objects_dir / f"{fingerprint}.json"

    def _load_index_locked(self) -> MutableMapping[str, Any]:
        if not self._index_path.exists():
            return {"version": 1, "transactions": {}}
        try:
            raw = json.loads(self._index_path.read_text(encoding="utf-8"))
        except Exception:
            return {"version": 1, "transactions": {}}
        if not isinstance(raw, dict):
            return {"version": 1, "transactions": {}}
        if "transactions" not in raw or not isinstance(raw.get("transactions"), dict):
            raw["transactions"] = {}
        raw.setdefault("version", 1)
        return raw  # type: ignore[return-value]

    def _save_index_locked(self, index: Mapping[str, Any]) -> None:
        _atomic_write_json(self._index_path, index)

    def _fingerprint_manifest(self, manifest: Mapping[str, Any]) -> ManifestFingerprint:
        payload = _stable_json(manifest).encode("utf-8", errors="surrogatepass")
        return hashlib.sha256(payload).hexdigest()

    def compute_workspace_file_hashes(self) -> dict[str, dict[str, Any]]:
        """Compute deterministic file-hash metadata used in stage fingerprints."""

        files: list[Path] = [
            self._repo_root / "DESIGNATED_AGENTS_LIST.md",
            self._repo_root / "PF_REPO_INVENTORY_LIST",
            self._repo_root / "schema" / "intake_handshake.json",
            self._repo_root / "schema" / "architecture_blueprint.json",
            self._repo_root / "schema" / "risk_clearance.json",
        ]
        out: dict[str, dict[str, Any]] = {}
        for p in files:
            digest = _sha256_file(p)
            if digest is None:
                continue
            try:
                st = p.stat()
                out[str(p.relative_to(self._repo_root))] = {"sha256": digest, "size": int(st.st_size)}
            except OSError:
                out[str(p.relative_to(self._repo_root))] = {"sha256": digest}
        return out

    async def run_stage(
        self,
        *,
        sandbox_run: Callable[..., Any],
        label: str,
        stage: PipelineStage,
        agent: object,
        fn_name: str,
        fn_args: Sequence[Any] = (),
        fn_kwargs: Mapping[str, Any] | None = None,
        timeout_s: float | None = None,
        mode: str = "auto",
        workdir: str | os.PathLike[str] | None = None,
        tracer: TelemetryTracer | None = None,
        correlation_id: str | None = None,
        transaction_id: str | None = None,
        workspace_file_hashes: Mapping[str, Any] | None = None,
        upstream_fingerprints: Sequence[ManifestFingerprint] = (),
    ) -> tuple[Any, CacheDecision]:
        """Return stage output, serving from cache when possible."""

        call_kwargs = dict(fn_kwargs or {})
        agent_meta = {
            "role": getattr(agent, "role", None),
            "module": getattr(agent.__class__, "__module__", None),
            "class": getattr(agent.__class__, "__name__", None),
            "config": getattr(agent, "config", None),
            "fn": fn_name,
            "label": label,
        }
        manifest: dict[str, Any] = {
            "agent": agent_meta,
            "call": {"args": list(fn_args), "kwargs": call_kwargs},
            "workspace_files": dict(workspace_file_hashes or {}),
            "upstream": list(upstream_fingerprints),
        }
        fp = self._fingerprint_manifest(manifest)

        def _try_load() -> dict[str, Any] | None:
            path = self._object_path(fp)
            if not path.exists():
                return None
            try:
                obj = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                return None
            return obj if isinstance(obj, dict) else None

        cached = await asyncio.to_thread(_try_load)
        if cached is not None and isinstance(cached.get("output_json"), str):
            output_json = str(cached["output_json"])
            try:
                result_obj = json.loads(output_json)
            except Exception:
                result_obj = None
            decision = CacheDecision(
                fingerprint=fp,
                cache_state="CACHE_HIT",
                telemetry=CacheTelemetry(
                    wall_ms=0.0,
                    cpu_ms=0.0,
                    bytes_transferred=len(output_json.encode("utf-8", errors="replace")),
                    sandbox_mode="cache",
                    sandbox_trace=str(cached.get("telemetry", {}).get("sandbox_trace") or ""),
                ),
            )
            if tracer is not None and correlation_id is not None:
                tracer.record(
                    correlation_id=correlation_id,
                    stage=stage,
                    event="CACHE_HIT",
                    payload_bytes=decision.telemetry.bytes_transferred,
                    latency_ms=0.0,
                )
            return result_obj, decision

        metrics: dict[str, Any] = {}

        def _metrics_hook(m: Any) -> None:
            # SandboxMetrics is defined in core.sandbox; keep a duck-typed hook here.
            try:
                metrics.update(
                    {
                        "wall_ms": float(getattr(m, "wall_ms", 0.0)),
                        "cpu_ms": float(getattr(m, "cpu_ms", 0.0)),
                        "input_bytes": int(getattr(m, "input_bytes", 0)),
                        "output_bytes": int(getattr(m, "output_bytes", 0)),
                        "sandbox_mode": str(getattr(m, "mode", "")),
                        "sandbox_trace": str(getattr(m, "trace_token", "")),
                    }
                )
            except Exception:
                return

        result_obj = await sandbox_run(
            label,
            getattr(agent, fn_name),
            *fn_args,
            fn_kwargs=call_kwargs,
            timeout_s=timeout_s,
            mode=mode,
            workdir=workdir,
            metrics_hook=_metrics_hook,
        )

        output_json = _stable_json(result_obj)

        def _store_and_index() -> None:
            now = time.time()
            obj_path = self._object_path(fp)
            obj_payload: dict[str, Any] = {
                "version": 1,
                "fingerprint": fp,
                "created_at": now,
                "cache_state": "CACHE_HIT",
                "output_json": output_json,
                "telemetry": {
                    "wall_ms": float(metrics.get("wall_ms") or 0.0),
                    "cpu_ms": float(metrics.get("cpu_ms") or 0.0),
                    "bytes_transferred": int(metrics.get("input_bytes") or 0) + int(metrics.get("output_bytes") or 0),
                    "sandbox_mode": str(metrics.get("sandbox_mode") or ""),
                    "sandbox_trace": str(metrics.get("sandbox_trace") or ""),
                },
                "manifest": manifest,
            }
            with self._lock:
                _atomic_write_json(obj_path, obj_payload)
                if transaction_id is None:
                    return
                index = self._load_index_locked()
                tx = index.setdefault("transactions", {}).setdefault(str(transaction_id), {})
                if not isinstance(tx, dict):
                    tx = {}
                    index["transactions"][str(transaction_id)] = tx
                # Cascading invalidation for this transaction: a miss at an upstream
                # stage dirties all downstream stages.
                try:
                    stage_idx = self._STAGE_ORDER.index(stage)
                except ValueError:
                    stage_idx = -1
                if stage_idx >= 0:
                    for s in self._STAGE_ORDER[stage_idx + 1 :]:
                        tx.pop(s, None)
                tx[stage] = fp
                self._save_index_locked(index)

        await asyncio.to_thread(_store_and_index)

        wall_ms = float(metrics.get("wall_ms") or 0.0)
        out_bytes = len(output_json.encode("utf-8", errors="replace"))
        transferred = int(metrics.get("input_bytes") or 0) + int(metrics.get("output_bytes") or out_bytes)
        decision = CacheDecision(
            fingerprint=fp,
            cache_state="CACHE_MISS",
            telemetry=CacheTelemetry(
                wall_ms=wall_ms,
                cpu_ms=float(metrics.get("cpu_ms") or 0.0),
                bytes_transferred=transferred,
                sandbox_mode=str(metrics.get("sandbox_mode") or ""),
                sandbox_trace=str(metrics.get("sandbox_trace") or ""),
            ),
        )
        if tracer is not None and correlation_id is not None:
            tracer.record(
                correlation_id=correlation_id,
                stage=stage,
                event="CACHE_MISS",
                payload_bytes=out_bytes,
                latency_ms=wall_ms,
            )
        return result_obj, decision

