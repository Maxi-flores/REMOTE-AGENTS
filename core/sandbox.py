"""Async-safe hybrid sandbox executor for agent workloads (stdlib-only).

This module exists to prevent CPU-bound or blocking agent logic from freezing
the main asyncio event loop. It provides a single entrypoint,
:class:`AgentSandboxExecutor`, which can offload work into:

- inline execution (only for very small work items)
- a shared ThreadPoolExecutor (context-propagating)
- an isolated subprocess per call (hard timeout + kill)

Process offloading uses a JSON payload frame for cross-boundary marshalling,
and returns execution metrics that can be recorded into core.telemetry without
impacting ring buffer sequence numbering (the main process remains the sole
writer).
"""

from __future__ import annotations

import asyncio
import contextvars
import inspect
import json
import os
import pickle
import tempfile
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from multiprocessing import get_context
from pathlib import Path
from typing import Any, Callable, Literal, Mapping, MutableMapping, TypeVar, cast

from core.exceptions import PipelineHaltException
from core.hashutil import fnv1a_32
from core.telemetry import PipelineStage, TelemetryTracer
from core.transaction_manager import current_transaction

T = TypeVar("T")

SandboxMode = Literal["auto", "inline", "thread", "process"]


@dataclass(frozen=True, slots=True)
class SandboxMetrics:
    wall_ms: float
    cpu_ms: float
    input_bytes: int
    output_bytes: int
    trace_token: str
    mode: Literal["inline", "thread", "process"]


def _json_dumps(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _json_bytes(obj: object) -> bytes:
    return _json_dumps(obj).encode("utf-8")


def _best_effort_bytes(obj: object) -> int:
    try:
        return len(_json_bytes(obj))
    except Exception:
        try:
            return len(repr(obj).encode("utf-8", errors="replace"))
        except Exception:
            return 0


def _is_pickleable(obj: object) -> bool:
    try:
        pickle.dumps(obj)
        return True
    except Exception:
        return False


def _safe_default_workdir(workdir: str | os.PathLike[str] | None) -> str | None:
    if workdir is None:
        return None
    return str(Path(workdir))


def _best_process_context():
    # Prefer fork on POSIX to avoid re-executing the test runner / __main__
    # module under multiprocessing "spawn" semantics.
    if os.name == "posix":
        try:
            return get_context("fork")
        except Exception:
            return get_context("spawn")
    return get_context("spawn")


def _subprocess_entry(  # pragma: no cover - executed in child process
    q,  # multiprocessing.Queue[dict[str, Any]]
    fn: Callable[..., Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    *,
    workdir: str | None,
) -> None:
    try:
        if workdir is not None:
            os.chdir(workdir)
        started = time.perf_counter()
        cpu_started = time.process_time()
        input_frame = {"args": args, "kwargs": kwargs}
        input_json = _json_dumps(input_frame)
        input_bytes = len(input_json.encode("utf-8"))
        result = fn(*args, **kwargs)
        if inspect.isawaitable(result):
            result = asyncio.run(cast(Any, result))
        result_json = _json_dumps(result)
        cpu_ms = (time.process_time() - cpu_started) * 1000.0
        wall_ms = (time.perf_counter() - started) * 1000.0
        out_bytes = len(result_json.encode("utf-8"))
        trace_token = fnv1a_32(
            _json_dumps(
                {
                    "mode": "process",
                    "input": input_json,
                    "output": result_json,
                    "wall_ms": wall_ms,
                    "cpu_ms": cpu_ms,
                }
            )
        )
        q.put(
            {
                "ok": True,
                "result_json": result_json,
                "metrics": {
                    "wall_ms": wall_ms,
                    "cpu_ms": cpu_ms,
                    "input_bytes": input_bytes,
                    "output_bytes": out_bytes,
                    "trace_token": trace_token,
                },
            }
        )
    except BaseException as exc:
        q.put(
            {
                "ok": False,
                "error": repr(exc),
                "traceback": traceback.format_exc(),
            }
        )


class _OffloadDirector:
    def __init__(
        self,
        *,
        inline_budget_ms: float,
        thread_budget_ms: float,
    ) -> None:
        self._inline_budget_ms = inline_budget_ms
        self._thread_budget_ms = thread_budget_ms
        self._ewma_ms: MutableMapping[str, float] = {}

    def record(self, label: str, wall_ms: float) -> None:
        prev = self._ewma_ms.get(label)
        if prev is None:
            self._ewma_ms[label] = wall_ms
            return
        # Light EWMA: new contributes 20%.
        self._ewma_ms[label] = (prev * 0.8) + (wall_ms * 0.2)

    def choose(self, label: str) -> Literal["inline", "thread", "process"]:
        avg = self._ewma_ms.get(label, self._thread_budget_ms + 1.0)
        if avg <= self._inline_budget_ms:
            return "inline"
        if avg <= self._thread_budget_ms:
            return "thread"
        return "process"


class AgentSandboxExecutor:
    """Hybrid offloading executor to keep the asyncio loop non-blocking."""

    def __init__(
        self,
        *,
        inline_budget_ms: float = 1.0,
        thread_budget_ms: float = 25.0,
        thread_workers: int | None = None,
    ) -> None:
        self._director = _OffloadDirector(inline_budget_ms=inline_budget_ms, thread_budget_ms=thread_budget_ms)
        self._thread_workers = thread_workers
        self._threads: ThreadPoolExecutor | None = None
        self._closed = False

    def _thread_executor(self) -> ThreadPoolExecutor:
        ex = self._threads
        if ex is not None:
            return ex
        ex = ThreadPoolExecutor(
            max_workers=self._thread_workers,
            thread_name_prefix="agent-sandbox",
        )
        self._threads = ex
        return ex

    async def __aenter__(self) -> "AgentSandboxExecutor":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:  # type: ignore[no-untyped-def]
        await self.aclose()
        return False

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        # Shutdown can block; keep it off the event loop thread.
        if self._threads is not None:
            await asyncio.to_thread(self._threads.shutdown, wait=True, cancel_futures=True)

    async def run(
        self,
        label: str,
        fn: Callable[..., T] | Callable[..., Awaitable[T]],
        /,
        *fn_args: Any,
        fn_kwargs: Mapping[str, Any] | None = None,
        timeout_s: float | None = None,
        mode: SandboxMode = "auto",
        workdir: str | os.PathLike[str] | None = None,
        tracer: TelemetryTracer | None = None,
        correlation_id: str | None = None,
        stage: PipelineStage | None = None,
        event: str = "SANDBOX_RUN",
        telemetry_metadata: Mapping[str, Any] | None = None,
    ) -> T:
        if self._closed:
            raise RuntimeError("AgentSandboxExecutor is closed")

        effective_workdir = _safe_default_workdir(workdir)
        requested_mode = mode

        if mode == "auto":
            chosen = self._director.choose(label)
        else:
            chosen = cast(Literal["inline", "thread", "process"], mode)

        started = time.perf_counter()
        call_kwargs = dict(fn_kwargs or {})

        # If we cannot pickle the callable/args, process mode is not viable.
        if chosen == "process":
            if current_transaction() is not None:
                chosen = "thread"
            elif not (_is_pickleable(fn) and _is_pickleable(fn_args) and _is_pickleable(call_kwargs)):
                chosen = "thread"
            else:
                # Require JSON-marshalable data frames for process isolation.
                try:
                    _json_dumps({"args": fn_args, "kwargs": call_kwargs})
                except Exception:
                    chosen = "thread"

        if requested_mode == "process" and chosen != "process":
            raise PipelineHaltException(f"{label} cannot run in process sandbox (fell back to {chosen})")

        async def _invoke() -> tuple[T, SandboxMetrics]:
            if chosen == "inline":
                result = fn(*fn_args, **call_kwargs)
                if inspect.isawaitable(result):
                    result = await cast(Any, result)
                wall_ms = (time.perf_counter() - started) * 1000.0
                input_bytes = _best_effort_bytes({"args": fn_args, "kwargs": call_kwargs})
                output_bytes = _best_effort_bytes(result)
                metrics = SandboxMetrics(
                    wall_ms=wall_ms,
                    cpu_ms=0.0,
                    input_bytes=input_bytes,
                    output_bytes=output_bytes,
                    trace_token=fnv1a_32(f"{label}:inline:{wall_ms:.3f}:{input_bytes}:{output_bytes}"),
                    mode="inline",
                )
                return cast(T, result), metrics

            if chosen == "thread":
                ctx = contextvars.copy_context()

                def _runner() -> T:
                    def _call() -> T:
                        out = fn(*fn_args, **call_kwargs)
                        if inspect.isawaitable(out):
                            return cast(T, asyncio.run(cast(Any, out)))
                        return cast(T, out)

                    return ctx.run(_call)

                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(self._thread_executor(), _runner)
                wall_ms = (time.perf_counter() - started) * 1000.0
                input_bytes = _best_effort_bytes({"args": fn_args, "kwargs": call_kwargs})
                output_bytes = _best_effort_bytes(result)
                metrics = SandboxMetrics(
                    wall_ms=wall_ms,
                    cpu_ms=0.0,
                    input_bytes=input_bytes,
                    output_bytes=output_bytes,
                    trace_token=fnv1a_32(f"{label}:thread:{wall_ms:.3f}:{input_bytes}:{output_bytes}"),
                    mode="thread",
                )
                return cast(T, result), metrics

            # chosen == "process"
            ctx = _best_process_context()
            q = ctx.Queue(maxsize=1)
            proc_workdir = effective_workdir
            if proc_workdir is None:
                # Reduce accidental workspace writes for untrusted tasks.
                proc_workdir = tempfile.gettempdir()
            proc = ctx.Process(
                target=_subprocess_entry,
                args=(q, fn, fn_args, call_kwargs),
                kwargs={"workdir": proc_workdir},
                daemon=True,
            )
            proc.start()

            def _wait_result() -> dict[str, Any]:
                try:
                    payload = q.get(timeout=timeout_s if timeout_s is not None else None)
                except Exception as exc:
                    # No result within timeout; kill hard.
                    try:
                        if proc.is_alive():
                            try:
                                proc.kill()
                            except Exception:
                                proc.terminate()
                    finally:
                        try:
                            proc.join(timeout=0.2)
                        except Exception:
                            pass
                    raise TimeoutError(str(exc)) from exc
                finally:
                    try:
                        if proc.is_alive():
                            proc.join(timeout=0.05)
                    except Exception:
                        pass
                return cast(dict[str, Any], payload)

            payload = await asyncio.to_thread(_wait_result)
            if not bool(payload.get("ok")):
                err = str(payload.get("error") or "Sandboxed process failed")
                tb = str(payload.get("traceback") or "")
                raise PipelineHaltException(f"{label} failed in process sandbox: {err}\n{tb}".strip())

            result_json = payload.get("result_json")
            if not isinstance(result_json, str):
                raise PipelineHaltException(f"{label} returned invalid process frame (missing result_json)")
            try:
                result_obj = json.loads(result_json)
            except Exception as exc:
                raise PipelineHaltException(f"{label} returned non-JSON result from process sandbox") from exc
            metrics_raw = cast(Mapping[str, Any], payload.get("metrics") or {})
            wall_ms = float(metrics_raw.get("wall_ms") or 0.0)
            metrics = SandboxMetrics(
                wall_ms=wall_ms,
                cpu_ms=float(metrics_raw.get("cpu_ms") or 0.0),
                input_bytes=int(metrics_raw.get("input_bytes") or 0),
                output_bytes=int(metrics_raw.get("output_bytes") or 0),
                trace_token=str(metrics_raw.get("trace_token") or ""),
                mode="process",
            )
            return cast(T, result_obj), metrics

        try:
            if timeout_s is None:
                result, metrics = await _invoke()
            else:
                result, metrics = await asyncio.wait_for(_invoke(), timeout=timeout_s)
        except TimeoutError as exc:
            raise PipelineHaltException(f"{label} sandbox timeout (mode={chosen}, timeout_s={timeout_s})") from exc
        except asyncio.TimeoutError as exc:
            raise PipelineHaltException(f"{label} sandbox timeout (mode={chosen}, timeout_s={timeout_s})") from exc

        self._director.record(label, metrics.wall_ms)

        if tracer is not None and correlation_id is not None and stage is not None:
            meta: dict[str, Any] = dict(telemetry_metadata or {})
            meta.update(
                {
                    "sandbox_mode": metrics.mode,
                    "sandbox_wall_ms": metrics.wall_ms,
                    "sandbox_cpu_ms": metrics.cpu_ms,
                    "sandbox_trace": metrics.trace_token,
                    "sandbox_label": label,
                }
            )
            tracer.record(
                correlation_id=correlation_id,
                stage=stage,
                event=event,
                payload_bytes=metrics.output_bytes,
                latency_ms=metrics.wall_ms,
                metadata=meta,
            )

        return result
