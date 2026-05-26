import asyncio
import json
import re
import shutil
import time
import unittest
from dataclasses import dataclass
from pathlib import Path

from core.dag_engine import NodeSpec, WorkspaceDAGEngine


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _extract_ms(event: str) -> int | None:
    m = re.search(r":t=(\d+)", event)
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


@dataclass(slots=True)
class _SleepyAgent:
    role: str
    config: dict
    delay_s: float = 0.0
    write_path: Path | None = None
    write_text: str | None = None

    async def run(self, *, payload=None, payloads=None):  # type: ignore[no-untyped-def]
        await asyncio.sleep(self.delay_s)
        if self.write_path is not None and self.write_text is not None:
            with open(self.write_path, "w", encoding="utf-8") as f:
                f.write(self.write_text)
                f.flush()
        return {"role": self.role, "payload": payload, "payloads": payloads, "wall_ms": int(self.delay_s * 1000)}


class TestReactiveDAGRig(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[1]
        self.logs_dir = self.repo_root / "logs"
        self.cache_root = self.repo_root / ".workspace_cache"
        self.telemetry_path = self.logs_dir / "TELEMETRY_TRACE.json"

        self._restore_text: dict[Path, str | None] = {}
        for path in (self.telemetry_path,):
            self._restore_text[path] = path.read_text(encoding="utf-8") if path.exists() else None

        self._cache_existed = self.cache_root.exists()
        if self.cache_root.exists():
            shutil.rmtree(self.cache_root)

        self._touched_paths: list[Path] = []

    async def asyncTearDown(self) -> None:
        if not self._cache_existed and self.cache_root.exists():
            shutil.rmtree(self.cache_root)

        for path, prior in self._restore_text.items():
            if prior is None:
                if path.exists():
                    path.unlink()
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(prior, encoding="utf-8")

        for p in self._touched_paths:
            try:
                p.unlink(missing_ok=True)
            except OSError:
                pass

        if self.logs_dir.exists() and not any(self.logs_dir.iterdir()):
            try:
                self.logs_dir.rmdir()
            except OSError:
                pass

    def _trace_records(self) -> list[dict]:
        self.assertTrue(self.telemetry_path.exists(), "Expected logs/TELEMETRY_TRACE.json to be written")
        loaded = _load_json(self.telemetry_path)
        self.assertIsInstance(loaded, list)
        return loaded  # type: ignore[return-value]

    async def test_01_parallel_concurrency_overlapping_sas_timelines(self) -> None:
        engine = WorkspaceDAGEngine(repo_root=self.repo_root, logs_dir=self.logs_dir)

        isa = _SleepyAgent(role="ISA", config={"node": "ISA"}, delay_s=0.01)
        sas_core = _SleepyAgent(role="SAS", config={"node": "SAS_Core"}, delay_s=0.15)
        sas_sub = _SleepyAgent(role="SAS", config={"node": "SAS_Submodules"}, delay_s=0.15)
        crs = _SleepyAgent(role="CRS", config={"node": "CRS"}, delay_s=0.01)
        boa = _SleepyAgent(role="BOA", config={"node": "BOA"}, delay_s=0.01)

        engine.add_nodes(
            [
                NodeSpec(node_id="ISA", stage="ISA", label="ISA", agent=isa, fn_name="run"),
                NodeSpec(
                    node_id="SAS_Core",
                    stage="SAS",
                    label="SAS_Core",
                    agent=sas_core,
                    fn_name="run",
                    depends_on=("ISA",),
                    upstream_kwargs={"payload": ("ISA",)},
                ),
                NodeSpec(
                    node_id="SAS_Submodules",
                    stage="SAS",
                    label="SAS_Submodules",
                    agent=sas_sub,
                    fn_name="run",
                    depends_on=("ISA",),
                    upstream_kwargs={"payload": ("ISA",)},
                ),
                NodeSpec(
                    node_id="CRS",
                    stage="CRS",
                    label="CRS",
                    agent=crs,
                    fn_name="run",
                    depends_on=("SAS_Core", "SAS_Submodules"),
                    upstream_kwargs={"payloads": ("SAS_Core", "SAS_Submodules")},
                ),
                NodeSpec(
                    node_id="BOA",
                    stage="BOA",
                    label="BOA",
                    agent=boa,
                    fn_name="run",
                    depends_on=("CRS",),
                    upstream_kwargs={"payload": ("CRS",)},
                ),
            ]
        )

        await engine.run(enable_prefetcher=False, correlation_id="dag-parallel", execution_token="dag-parallel-token")

        trace = self._trace_records()
        events = [str(r.get("event") or "") for r in trace]

        def _event_ms(prefix: str) -> int:
            for ev in events:
                if ev.startswith(prefix):
                    ms = _extract_ms(ev)
                    if ms is not None:
                        return ms
            raise AssertionError(f"Missing telemetry event prefix: {prefix}")

        start_core = _event_ms("DAG_NODE_START:SAS_Core")
        end_core = _event_ms("DAG_NODE_END:SAS_Core")
        start_sub = _event_ms("DAG_NODE_START:SAS_Submodules")
        end_sub = _event_ms("DAG_NODE_END:SAS_Submodules")

        self.assertLess(start_core, end_sub)
        self.assertLess(start_sub, end_core)

    async def test_02_predictive_warming_preregisters_child_cache_hits(self) -> None:
        # First run populates cache objects for the exact fingerprints.
        engine1 = WorkspaceDAGEngine(repo_root=self.repo_root, logs_dir=self.logs_dir)
        isa = _SleepyAgent(role="ISA", config={"node": "ISA"}, delay_s=0.01)
        sas_core = _SleepyAgent(role="SAS", config={"node": "SAS_Core"}, delay_s=0.05)
        sas_sub = _SleepyAgent(role="SAS", config={"node": "SAS_Submodules"}, delay_s=0.05)
        crs = _SleepyAgent(role="CRS", config={"node": "CRS"}, delay_s=0.01)

        engine1.add_nodes(
            [
                NodeSpec(node_id="ISA", stage="ISA", label="ISA", agent=isa, fn_name="run"),
                NodeSpec(
                    node_id="SAS_Core",
                    stage="SAS",
                    label="SAS_Core",
                    agent=sas_core,
                    fn_name="run",
                    depends_on=("ISA",),
                    upstream_kwargs={"payload": ("ISA",)},
                ),
                NodeSpec(
                    node_id="SAS_Submodules",
                    stage="SAS",
                    label="SAS_Submodules",
                    agent=sas_sub,
                    fn_name="run",
                    depends_on=("ISA",),
                    upstream_kwargs={"payload": ("ISA",)},
                ),
                NodeSpec(
                    node_id="CRS",
                    stage="CRS",
                    label="CRS",
                    agent=crs,
                    fn_name="run",
                    depends_on=("SAS_Core", "SAS_Submodules"),
                    upstream_kwargs={"payloads": ("SAS_Core", "SAS_Submodules")},
                ),
            ]
        )
        await engine1.run(enable_prefetcher=False, correlation_id="dag-prefetch-seed", execution_token="dag-prefetch-token")

        # Second run: gate SAS nodes to simulate a queue delay; prefetcher should
        # pre-register cache hits before gates are released.
        core_gate = asyncio.Event()
        sub_gate = asyncio.Event()
        engine2 = WorkspaceDAGEngine(repo_root=self.repo_root, logs_dir=self.logs_dir)
        engine2.add_nodes(
            [
                NodeSpec(node_id="ISA", stage="ISA", label="ISA", agent=isa, fn_name="run"),
                NodeSpec(
                    node_id="SAS_Core",
                    stage="SAS",
                    label="SAS_Core",
                    agent=sas_core,
                    fn_name="run",
                    depends_on=("ISA",),
                    upstream_kwargs={"payload": ("ISA",)},
                    start_gate=core_gate,
                ),
                NodeSpec(
                    node_id="SAS_Submodules",
                    stage="SAS",
                    label="SAS_Submodules",
                    agent=sas_sub,
                    fn_name="run",
                    depends_on=("ISA",),
                    upstream_kwargs={"payload": ("ISA",)},
                    start_gate=sub_gate,
                ),
                NodeSpec(
                    node_id="CRS",
                    stage="CRS",
                    label="CRS",
                    agent=crs,
                    fn_name="run",
                    depends_on=("SAS_Core", "SAS_Submodules"),
                    upstream_kwargs={"payloads": ("SAS_Core", "SAS_Submodules")},
                ),
            ]
        )

        watch_path = self.repo_root / "PREFETCH_WATCH.txt"
        watch_path.write_text("v1\n", encoding="utf-8")
        self._touched_paths.append(watch_path)

        run_task = asyncio.create_task(
            engine2.run(
                enable_prefetcher=True,
                correlation_id="dag-prefetch",
                execution_token="dag-prefetch-token",
                prefetch_watch_paths=(watch_path,),
                prefetch_poll_s=0.01,
            )
        )

        # Mutate an upstream component (watched file) to force a prefetch tick.
        watch_path.write_text(f"v2:{time.time()}\n", encoding="utf-8")

        deadline = time.time() + 2.0
        while time.time() < deadline:
            if self.telemetry_path.exists():
                trace = self._trace_records()
                hit_events = [r for r in trace if str(r.get("event") or "").startswith("PREDICTIVE_CACHE_HIT:")]
                if hit_events:
                    break
            await asyncio.sleep(0.02)
        else:
            raise AssertionError("Timed out waiting for PREDICTIVE_CACHE_HIT event")

        # Release the gates so the run can finish (nodes should already be done).
        core_gate.set()
        sub_gate.set()
        results = await asyncio.wait_for(run_task, timeout=5.0)

        self.assertEqual(results["SAS_Core"].cache_state, "PREDICTIVE_CACHE_HIT")
        self.assertEqual(results["SAS_Submodules"].cache_state, "PREDICTIVE_CACHE_HIT")

        # SAS nodes should not actually start when pre-registered.
        trace = self._trace_records()
        sas_starts = [
            r
            for r in trace
            if str(r.get("event") or "").startswith("DAG_NODE_START:SAS_") and str(r.get("correlation_id") or "") == "dag-prefetch"
        ]
        self.assertEqual(sas_starts, [])

    async def test_03_isolation_safeguards_concurrent_writes_commit_cleanly(self) -> None:
        engine = WorkspaceDAGEngine(repo_root=self.repo_root, logs_dir=self.logs_dir)

        out_core = self.repo_root / "DAG_WRITE_CORE.txt"
        out_sub = self.repo_root / "DAG_WRITE_SUB.txt"
        self._touched_paths.extend([out_core, out_sub])

        isa = _SleepyAgent(role="ISA", config={"node": "ISA"}, delay_s=0.01)
        sas_core = _SleepyAgent(
            role="SAS",
            config={"node": "SAS_Core"},
            delay_s=0.05,
            write_path=out_core,
            write_text="core\n",
        )
        sas_sub = _SleepyAgent(
            role="SAS",
            config={"node": "SAS_Submodules"},
            delay_s=0.05,
            write_path=out_sub,
            write_text="submodules\n",
        )
        crs = _SleepyAgent(role="CRS", config={"node": "CRS"}, delay_s=0.01)

        engine.add_nodes(
            [
                NodeSpec(node_id="ISA", stage="ISA", label="ISA", agent=isa, fn_name="run"),
                NodeSpec(
                    node_id="SAS_Core",
                    stage="SAS",
                    label="SAS_Core",
                    agent=sas_core,
                    fn_name="run",
                    depends_on=("ISA",),
                    upstream_kwargs={"payload": ("ISA",)},
                ),
                NodeSpec(
                    node_id="SAS_Submodules",
                    stage="SAS",
                    label="SAS_Submodules",
                    agent=sas_sub,
                    fn_name="run",
                    depends_on=("ISA",),
                    upstream_kwargs={"payload": ("ISA",)},
                ),
                NodeSpec(
                    node_id="CRS",
                    stage="CRS",
                    label="CRS",
                    agent=crs,
                    fn_name="run",
                    depends_on=("SAS_Core", "SAS_Submodules"),
                    upstream_kwargs={"payloads": ("SAS_Core", "SAS_Submodules")},
                ),
            ]
        )

        await engine.run(enable_prefetcher=False, correlation_id="dag-isolation", execution_token="dag-isolation-token")

        self.assertTrue(out_core.exists())
        self.assertTrue(out_sub.exists())
        self.assertEqual(out_core.read_text(encoding="utf-8"), "core\n")
        self.assertEqual(out_sub.read_text(encoding="utf-8"), "submodules\n")

        staging = self.repo_root / ".workspace_staging" / "dag-isolation-token"
        self.assertFalse(staging.exists(), "Expected transaction staging to be cleaned after commits")

        trace = self._trace_records()
        ends = [str(r.get("event") or "") for r in trace if str(r.get("event") or "").startswith("DAG_NODE_END:")]
        self.assertTrue(any(":fp=" in ev for ev in ends), "Expected DAG_NODE_END events to include fingerprints")


if __name__ == "__main__":
    unittest.main(verbosity=2)

