"""Reactive DAG execution engine with predictive cache warming (stdlib-only).

This module extends the linear ISA->SAS->CRS->BOA pipeline concept into a
non-linear dependency graph that can execute independent branches concurrently.

Key goals:
- asyncio-native parallel execution with dependency-aware scheduling
- WorkspaceCacheEngine integration (content-addressed cache objects)
- Predictive prefetch loop that can pre-register downstream cache hits
- Isolation via WorkspaceTransaction copy-on-write contexts per node execution
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable, Iterable, Mapping, MutableMapping, Sequence

from core.cache import ManifestFingerprint, WorkspaceCacheEngine
from core.sandbox import AgentSandboxExecutor
from core.telemetry import PipelineStage, TelemetryTracer
from core.transaction_manager import WorkspaceTransaction


def _stable_json(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_file(path: Path) -> str | None:
    try:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def _now_ms() -> int:
    return int(time.time() * 1000.0)


class _CompatTaskGroup:
    """asyncio.TaskGroup compatible subset for Python 3.10+."""

    def __init__(self) -> None:
        self._tasks: list[asyncio.Task[object]] = []

    async def __aenter__(self) -> "_CompatTaskGroup":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:  # type: ignore[no-untyped-def]
        if not self._tasks:
            return False
        try:
            await asyncio.gather(*self._tasks)
        finally:
            self._tasks.clear()
        return False

    def create_task(self, coro: Awaitable[object]) -> asyncio.Task[object]:
        t = asyncio.create_task(coro)
        self._tasks.append(t)
        return t


try:  # pragma: no cover - depends on runtime python
    from asyncio import TaskGroup as _TaskGroup  # type: ignore[attr-defined]
except Exception:  # pragma: no cover
    _TaskGroup = _CompatTaskGroup  # type: ignore[assignment]


@dataclass(frozen=True, slots=True)
class NodeSpec:
    """Single DAG execution node."""

    node_id: str
    stage: PipelineStage
    label: str
    agent: object
    fn_name: str
    depends_on: tuple[str, ...] = ()
    upstream_kwargs: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    fn_args: tuple[Any, ...] = ()
    fn_kwargs: Mapping[str, Any] = field(default_factory=dict)
    input_files: tuple[Path, ...] = ()
    timeout_s: float | None = None
    mode: str = "auto"
    workdir: str | os.PathLike[str] | None = None
    start_gate: asyncio.Event | None = None


@dataclass(slots=True)
class NodeResult:
    value: Any
    fingerprint: ManifestFingerprint
    cache_state: str  # "CACHE_HIT" | "CACHE_MISS" | "PREDICTIVE_CACHE_HIT"


@dataclass(slots=True)
class _NodeRuntime:
    spec: NodeSpec
    status: str = "pending"  # pending|running|done|failed
    result: NodeResult | None = None
    error: BaseException | None = None
    done: asyncio.Event = field(default_factory=asyncio.Event)


class WorkspaceDAGEngine:
    """Reactive DAG executor with cache integration and isolation rings."""

    def __init__(
        self,
        *,
        repo_root: Path,
        logs_dir: Path | None = None,
        cache_root: Path | None = None,
        tracer: TelemetryTracer | None = None,
        cache: WorkspaceCacheEngine | None = None,
        sandbox: AgentSandboxExecutor | None = None,
    ) -> None:
        self._repo_root = repo_root.resolve()
        self._logs_dir = (logs_dir or (self._repo_root / "logs")).resolve()
        self._cache = cache or WorkspaceCacheEngine(repo_root=self._repo_root, cache_root=cache_root)
        self._tracer = tracer or TelemetryTracer(logs_dir=self._logs_dir)
        self._sandbox = sandbox
        self._owns_sandbox = sandbox is None
        self._active_sandbox: AgentSandboxExecutor | None = None
        self._nodes: dict[str, _NodeRuntime] = {}
        self._dependents: dict[str, list[str]] = {}
        self._state_mu = asyncio.Lock()
        self._flush_mu = asyncio.Lock()
        self._flush_pending: asyncio.Task[None] | None = None

    @property
    def tracer(self) -> TelemetryTracer:
        return self._tracer

    @property
    def cache(self) -> WorkspaceCacheEngine:
        return self._cache

    def add_node(self, spec: NodeSpec) -> None:
        if spec.node_id in self._nodes:
            raise ValueError(f"Duplicate node_id: {spec.node_id}")
        self._nodes[spec.node_id] = _NodeRuntime(spec=spec)
        self._dependents.setdefault(spec.node_id, [])
        for parent in spec.depends_on:
            self._dependents.setdefault(parent, []).append(spec.node_id)

    def add_nodes(self, specs: Iterable[NodeSpec]) -> None:
        for spec in specs:
            self.add_node(spec)

    def _workspace_hashes_for_node(self, spec: NodeSpec) -> dict[str, dict[str, Any]]:
        base = self._cache.compute_workspace_file_hashes()
        for p in spec.input_files:
            abs_path = p if p.is_absolute() else (self._repo_root / p)
            abs_path = abs_path.resolve()
            digest = _sha256_file(abs_path)
            if digest is None:
                continue
            key = str(abs_path.relative_to(self._repo_root)) if abs_path.is_relative_to(self._repo_root) else str(abs_path)
            try:
                st = abs_path.stat()
                base[key] = {"sha256": digest, "size": int(st.st_size)}
            except OSError:
                base[key] = {"sha256": digest}
        return base

    def _fingerprint_for(
        self,
        *,
        spec: NodeSpec,
        upstream_fingerprints: Sequence[ManifestFingerprint],
        workspace_file_hashes: Mapping[str, Any],
        fn_args: Sequence[Any],
        fn_kwargs: Mapping[str, Any],
    ) -> ManifestFingerprint:
        call_kwargs = dict(fn_kwargs)
        agent_meta = {
            "role": getattr(spec.agent, "role", None),
            "module": getattr(spec.agent.__class__, "__module__", None),
            "class": getattr(spec.agent.__class__, "__name__", None),
            "config": getattr(spec.agent, "config", None),
            "fn": spec.fn_name,
            "label": spec.label,
        }
        manifest: dict[str, Any] = {
            "agent": agent_meta,
            "call": {"args": list(fn_args), "kwargs": call_kwargs},
            "workspace_files": dict(workspace_file_hashes),
            "upstream": list(upstream_fingerprints),
        }
        payload = _stable_json(manifest).encode("utf-8", errors="surrogatepass")
        return hashlib.sha256(payload).hexdigest()

    async def _record(self, *, correlation_id: str, stage: PipelineStage, event: str) -> None:
        self._tracer.record(
            correlation_id=correlation_id,
            stage=stage,
            event=event,
            payload_bytes=len(event.encode("utf-8", errors="replace")),
            latency_ms=0.0,
        )
        await self._flush_trace_soon()

    async def _flush_trace_soon(self) -> None:
        async with self._flush_mu:
            if self._flush_pending is not None and not self._flush_pending.done():
                return

            async def _flush() -> None:
                # Debounce slightly to batch concurrent records.
                await asyncio.sleep(0.005)
                await asyncio.to_thread(self._tracer.flush_trace)

            self._flush_pending = asyncio.create_task(_flush())

    async def _peek_cache_object(self, fingerprint: ManifestFingerprint) -> Any | None:
        cache_root = getattr(self._cache, "_cache_root", (self._repo_root / ".workspace_cache")).resolve()
        objects = cache_root / "objects"
        obj_path = objects / f"{fingerprint}.json"

        def _load() -> Any | None:
            if not obj_path.exists():
                return None
            try:
                raw = json.loads(obj_path.read_text(encoding="utf-8"))
            except Exception:
                return None
            if not isinstance(raw, dict) or not isinstance(raw.get("output_json"), str):
                return None
            try:
                return json.loads(str(raw["output_json"]))
            except Exception:
                return None

        return await asyncio.to_thread(_load)

    async def _prefetch_ready(self, *, correlation_id: str) -> int:
        """Attempt to pre-register cache hits for nodes that are ready but not started."""
        warmed = 0
        async with self._state_mu:
            candidates = [
                rt
                for rt in self._nodes.values()
                if rt.status == "pending" and all(self._nodes[d].status == "done" for d in rt.spec.depends_on)
            ]

        for rt in candidates:
            spec = rt.spec
            upstream_fps: list[ManifestFingerprint] = []
            async with self._state_mu:
                # Re-check in case scheduler raced.
                if rt.status != "pending":
                    continue
                for parent in spec.depends_on:
                    parent_res = self._nodes[parent].result
                    if parent_res is None:
                        upstream_fps = []
                        break
                    upstream_fps.append(parent_res.fingerprint)
            if not upstream_fps and spec.depends_on:
                continue
            workspace_hashes = self._workspace_hashes_for_node(spec)
            injected_kwargs = self._build_kwargs(spec)
            fp = self._fingerprint_for(
                spec=spec,
                upstream_fingerprints=upstream_fps,
                workspace_file_hashes=workspace_hashes,
                fn_args=spec.fn_args,
                fn_kwargs={**spec.fn_kwargs, **injected_kwargs},
            )
            cached = await self._peek_cache_object(fp)
            if cached is None:
                continue
            async with self._state_mu:
                if rt.status != "pending":
                    continue
                rt.status = "done"
                rt.result = NodeResult(value=cached, fingerprint=fp, cache_state="PREDICTIVE_CACHE_HIT")
                rt.done.set()
            warmed += 1
            await self._record(correlation_id=correlation_id, stage=spec.stage, event=f"PREDICTIVE_CACHE_HIT:{spec.node_id}")
        return warmed

    def _build_kwargs(self, spec: NodeSpec) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for k, refs in spec.upstream_kwargs.items():
            nodes = tuple(refs)
            if len(nodes) == 1:
                val = self._nodes[nodes[0]].result.value if self._nodes[nodes[0]].result is not None else None
                out[k] = val
            else:
                vals: list[Any] = []
                for nid in nodes:
                    res = self._nodes[nid].result
                    vals.append(res.value if res is not None else None)
                out[k] = vals
        return out

    async def run(
        self,
        *,
        correlation_id: str | None = None,
        execution_token: str | None = None,
        enable_prefetcher: bool = True,
        prefetch_poll_s: float = 0.02,
        prefetch_watch_paths: Sequence[Path] | None = None,
    ) -> Mapping[str, NodeResult]:
        if not self._nodes:
            raise ValueError("No DAG nodes registered")

        corr = correlation_id or uuid.uuid4().hex
        token = execution_token or uuid.uuid4().hex

        prefetcher: PredictivePrefetcher | None = None
        if enable_prefetcher:
            prefetcher = PredictivePrefetcher(
                engine=self,
                correlation_id=corr,
                poll_s=prefetch_poll_s,
                watch_paths=prefetch_watch_paths or (),
            )
            prefetcher.start()

        try:
            await self._record(correlation_id=corr, stage="ISA", event=f"DAG_START:token={token}")
            if self._owns_sandbox:
                sandbox = AgentSandboxExecutor()
                async with sandbox:
                    self._active_sandbox = sandbox
                    await self._execute_all(correlation_id=corr, execution_token=token)
            else:
                if self._sandbox is None:
                    raise RuntimeError("Sandbox executor missing")
                self._active_sandbox = self._sandbox
                await self._execute_all(correlation_id=corr, execution_token=token)
            await self._record(correlation_id=corr, stage="BOA", event="DAG_DONE")
            await asyncio.to_thread(self._tracer.flush_trace)
        finally:
            self._active_sandbox = None
            if prefetcher is not None:
                await prefetcher.aclose()
        return {node_id: rt.result for node_id, rt in self._nodes.items() if rt.result is not None}

    async def _execute_all(self, *, correlation_id: str, execution_token: str) -> None:
        remaining: dict[str, int] = {nid: len(rt.spec.depends_on) for nid, rt in self._nodes.items()}
        ready: list[str] = [nid for nid, count in remaining.items() if count == 0]
        processed: set[str] = set()
        done_q: asyncio.Queue[str] = asyncio.Queue()

        async def _runner(nid: str) -> None:
            await self._run_node(node_id=nid, correlation_id=correlation_id, execution_token=execution_token)
            done_q.put_nowait(nid)

        def _process_done(nid: str) -> None:
            if nid in processed:
                return
            processed.add(nid)
            for child in self._dependents.get(nid, []):
                remaining[child] -= 1
                if remaining[child] == 0:
                    ready.append(child)

        async with _TaskGroup() as tg:
            inflight: set[str] = set()
            while len(processed) < len(self._nodes):
                # Let the prefetcher opportunistically complete ready nodes.
                warmed = await self._prefetch_ready(correlation_id=correlation_id)
                if warmed:
                    for nid, rt in self._nodes.items():
                        if rt.status == "done":
                            _process_done(nid)

                # Schedule any nodes that have become ready.
                while ready:
                    nid = ready.pop(0)
                    rt = self._nodes[nid]
                    if rt.status == "done":
                        _process_done(nid)
                        continue
                    if rt.status == "failed":
                        raise RuntimeError(f"Node failed before scheduling: {nid}")
                    if nid in inflight:
                        continue
                    inflight.add(nid)

                    async def _wrap(n: str) -> None:
                        try:
                            await _runner(n)
                        finally:
                            inflight.discard(n)

                    tg.create_task(_wrap(nid))

                if len(processed) >= len(self._nodes):
                    break

                # Await progress from at least one running task or another prefetch tick.
                try:
                    nid = await asyncio.wait_for(done_q.get(), timeout=0.05)
                    _process_done(nid)
                except asyncio.TimeoutError:
                    continue

    async def _run_node(self, *, node_id: str, correlation_id: str, execution_token: str) -> None:
        rt = self._nodes[node_id]
        spec = rt.spec

        # Wait for any dependency results.
        for parent in spec.depends_on:
            await self._nodes[parent].done.wait()
            if self._nodes[parent].status == "failed":
                raise RuntimeError(f"Upstream failed: {parent}")

        if spec.start_gate is not None:
            await spec.start_gate.wait()

        async with self._state_mu:
            if rt.status == "done":
                return
            if rt.status != "pending":
                return
            rt.status = "running"

        upstream_fps: list[ManifestFingerprint] = []
        for parent in spec.depends_on:
            parent_res = self._nodes[parent].result
            if parent_res is None:
                continue
            upstream_fps.append(parent_res.fingerprint)

        injected_kwargs = self._build_kwargs(spec)
        fn_kwargs = {**spec.fn_kwargs, **injected_kwargs}
        workspace_hashes = self._workspace_hashes_for_node(spec)

        # Emit a DAG start marker for concurrency diagnostics.
        await self._record(
            correlation_id=correlation_id,
            stage=spec.stage,
            event=f"DAG_NODE_START:{spec.node_id}:t={_now_ms()}",
        )

        try:
            cache_root = getattr(self._cache, "_cache_root", (self._repo_root / ".workspace_cache")).resolve()
            exclude = [self._logs_dir, cache_root]
            with WorkspaceTransaction(
                repo_roots=[self._repo_root],
                token=execution_token,
                stage=spec.node_id,
                exclude_roots=exclude,
            ) as tx:
                sandbox = self._active_sandbox
                if sandbox is None:
                    raise RuntimeError("Sandbox executor not active")
                result_obj, decision = await self._cache.run_stage(
                    sandbox_run=sandbox.run,
                    label=spec.label,
                    stage=spec.stage,
                    agent=spec.agent,
                    fn_name=spec.fn_name,
                    fn_args=spec.fn_args,
                    fn_kwargs=fn_kwargs,
                    timeout_s=spec.timeout_s,
                    mode=spec.mode,
                    workdir=spec.workdir,
                    tracer=self._tracer,
                    correlation_id=correlation_id,
                    transaction_id=tx.token,
                    workspace_file_hashes=workspace_hashes,
                    upstream_fingerprints=tuple(upstream_fps),
                )
                tx.commit()
            node_result = NodeResult(value=result_obj, fingerprint=decision.fingerprint, cache_state=decision.cache_state)
        except BaseException as exc:
            async with self._state_mu:
                rt.status = "failed"
                rt.error = exc
                rt.done.set()
            await self._record(correlation_id=correlation_id, stage=spec.stage, event=f"DAG_NODE_FAIL:{spec.node_id}:{type(exc).__name__}")
            raise

        async with self._state_mu:
            rt.status = "done"
            rt.result = node_result
            rt.done.set()

        await self._record(
            correlation_id=correlation_id,
            stage=spec.stage,
            event=f"DAG_NODE_END:{spec.node_id}:t={_now_ms()}:fp={node_result.fingerprint}:cache={node_result.cache_state}",
        )

    # ---- Compilation helpers (Markdown -> DAG blueprint) ----

    @staticmethod
    def _parse_json_block(text: str) -> dict[str, Any]:
        m = re.search(r"```json\\s*(\\{.*?\\})\\s*```", text, flags=re.DOTALL)
        if not m:
            raise ValueError("No ```json block found")
        raw = json.loads(m.group(1))
        if not isinstance(raw, dict):
            raise ValueError("Designated agents JSON block must be an object")
        return raw

    @staticmethod
    def _parse_repo_inventory_projects(text: str) -> list[str]:
        projects: list[str] = []
        for ln in text.splitlines():
            ln = ln.strip()
            if not ln.startswith("|"):
                continue
            # Skip header separator rows.
            if ln.count("|") < 4:
                continue
            cells = [c.strip() for c in ln.strip("|").split("|")]
            if not cells:
                continue
            name = cells[0]
            if not name or name.lower() == "project" or set(name) == {"-"}:
                continue
            projects.append(name)
        # De-duplicate preserving order.
        out: list[str] = []
        seen: set[str] = set()
        for p in projects:
            if p in seen:
                continue
            seen.add(p)
            out.append(p)
        return out

    def compile_blueprint_from_workspace_files(self) -> dict[str, dict[str, Any]]:
        """Compile a non-linear DAG blueprint from markdown inventory sources.

        Returns a JSON-serializable blueprint (does not instantiate agents).
        """
        designated_path = self._repo_root / "DESIGNATED_AGENTS_LIST.md"
        inventory_path = self._repo_root / "PF_REPO_INVENTORY_LIST"
        designated = self._parse_json_block(designated_path.read_text(encoding="utf-8", errors="replace"))
        repos = self._parse_repo_inventory_projects(inventory_path.read_text(encoding="utf-8", errors="replace"))

        pipeline = designated.get("default_pipeline", [])
        agents = designated.get("agents", {})
        if not isinstance(pipeline, list) or not isinstance(agents, dict):
            raise ValueError("Invalid DESIGNATED_AGENTS_LIST.md payload")

        def _agent_spec(role: str) -> dict[str, Any]:
            raw = agents.get(role) if isinstance(agents, dict) else None
            if not isinstance(raw, dict):
                return {"role": role, "module": None, "class": None}
            return {"role": role, "module": raw.get("module"), "class": raw.get("class")}

        isa_role = str(pipeline[0]) if len(pipeline) > 0 else "intake_specialist"
        sas_role = str(pipeline[1]) if len(pipeline) > 1 else "software_architect"
        crs_role = str(pipeline[2]) if len(pipeline) > 2 else "risk_compliance"
        boa_role = str(pipeline[3]) if len(pipeline) > 3 else "build_orchestrator"

        sas_nodes = [f"SAS::{re.sub(r'\\s+', '_', r)}" for r in (repos[:64] or ["workspace"])]
        blueprint: dict[str, dict[str, Any]] = {}
        blueprint["ISA"] = {"stage": "ISA", "agent": _agent_spec(isa_role), "depends_on": []}
        for nid in sas_nodes:
            blueprint[nid] = {"stage": "SAS", "agent": _agent_spec(sas_role), "depends_on": ["ISA"]}
        blueprint["CRS"] = {"stage": "CRS", "agent": _agent_spec(crs_role), "depends_on": sas_nodes}
        blueprint["BOA"] = {"stage": "BOA", "agent": _agent_spec(boa_role), "depends_on": ["CRS"]}
        return blueprint


class PredictivePrefetcher:
    """Background poller that warms downstream cache objects opportunistically."""

    def __init__(
        self,
        *,
        engine: WorkspaceDAGEngine,
        correlation_id: str,
        poll_s: float = 0.02,
        watch_paths: Sequence[Path] = (),
    ) -> None:
        self._engine = engine
        self._correlation_id = correlation_id
        self._poll_s = max(0.005, float(poll_s))
        self._watch_paths = [p for p in watch_paths]
        self._telemetry_path = (engine._logs_dir / "TELEMETRY_TRACE.json").resolve()
        self._task: asyncio.Task[None] | None = None
        self._stopped = asyncio.Event()
        self._last_mtime: dict[Path, float] = {}

    def start(self) -> None:
        if self._task is not None:
            return
        self._task = asyncio.create_task(self._run())

    async def aclose(self) -> None:
        self._stopped.set()
        task = self._task
        if task is None:
            return
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        self._task = None

    def _changed(self, path: Path) -> bool:
        try:
            st = path.stat()
        except OSError:
            st = None
        mtime = float(st.st_mtime) if st is not None else -1.0
        prev = self._last_mtime.get(path)
        if prev is None or mtime != prev:
            self._last_mtime[path] = mtime
            return True
        return False

    async def _run(self) -> None:
        # Always monitor telemetry output.
        paths = [self._telemetry_path, *self._watch_paths]
        for p in paths:
            self._changed(p)
        while not self._stopped.is_set():
            changed = False
            for p in paths:
                if self._changed(p):
                    changed = True
            if changed:
                await self._engine._prefetch_ready(correlation_id=self._correlation_id)
            await asyncio.sleep(self._poll_s)
