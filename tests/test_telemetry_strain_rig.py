"""Telemetry concurrency and jitter strain rig.

This test module provides a highly parallel, stdlib-only stress harness that
targets:
1) bounded in-memory telemetry ring buffers (core.telemetry)
2) strict pipeline sequencing (core.matrix_verifier)
3) asyncio queue handoff resilience under jitter (core.handshake-style pipeline)

The rig is designed to surface:
- message ordering races / out-of-order bypass attempts
- ring-buffer eviction correctness and JSON trace integrity
- deadlocks or starvation caused by telemetry interceptors
"""

from __future__ import annotations

import asyncio
import json
import random
import time
import unittest
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from agents.registry import AgentRegistry
from core.exceptions import PipelineHaltException
from core.matrix_verifier import MatrixVerifier
from core.telemetry import TelemetryTracer
from core.validator import SchemaValidator
from core.handshake import TwinAuditor


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _payload_size_bytes(obj: object) -> int:
    try:
        return len(json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    except Exception:
        return 0


@dataclass(frozen=True, slots=True)
class _JitterProfile:
    """Jitter ranges (seconds) applied to each stage."""

    isa: tuple[float, float] = (0.0, 0.004)
    ita: tuple[float, float] = (0.0, 0.004)
    sas: tuple[float, float] = (0.0, 0.004)
    ata: tuple[float, float] = (0.0, 0.004)
    crs: tuple[float, float] = (0.0, 0.004)
    rta: tuple[float, float] = (0.0, 0.004)
    boa: tuple[float, float] = (0.0, 0.004)


async def _sleep_jitter(rng: random.Random, bounds: tuple[float, float]) -> None:
    low, high = bounds
    if high <= 0:
        return
    delay = low + (high - low) * rng.random()
    if delay > 0:
        await asyncio.sleep(delay)


async def _run_instrumented_handshake_once(
    *,
    repo_root: Path,
    logs_dir: Path,
    tracer: TelemetryTracer,
    verifier: MatrixVerifier,
    business_case: str,
    rng: random.Random,
    jitter: _JitterProfile,
    record_latency: Callable[[float], None],
) -> dict[str, Any]:
    """Run a queue-based ISA->SAS->CRS->BOA pipeline with telemetry interceptors.

    This is a test-only harness intentionally similar to core.handshake.HandshakePipeline,
    but with:
    - maxsize=1 queues (to amplify backpressure if interceptors block)
    - jittered delays and explicit latency sampling around verifier+tracer calls
    """

    registry = AgentRegistry(repo_root=repo_root, logs_dir=logs_dir)
    isa, sas, crs, _boa = registry.build(repository_name=repo_root.name)

    schema_dir = repo_root / "schema"
    validator = SchemaValidator(schema_dir)
    ita = TwinAuditor("ITA", validator, logs_dir)
    ata = TwinAuditor("ATA", validator, logs_dir)
    rta = TwinAuditor("RTA", validator, logs_dir)

    correlation_id = str(uuid.uuid4())

    q_isa_out: asyncio.Queue[dict | None] = asyncio.Queue(maxsize=1)
    q_sas_in: asyncio.Queue[dict | None] = asyncio.Queue(maxsize=1)
    q_sas_out: asyncio.Queue[dict | None] = asyncio.Queue(maxsize=1)
    q_crs_in: asyncio.Queue[dict | None] = asyncio.Queue(maxsize=1)
    q_crs_out: asyncio.Queue[dict | None] = asyncio.Queue(maxsize=1)
    q_boa_in: asyncio.Queue[dict | None] = asyncio.Queue(maxsize=1)

    def _intercept(stage: str, *, payload: object, event: str) -> None:
        start = time.perf_counter()
        verifier.verify_transition(correlation_id=correlation_id, stage=stage, payload={"event": event})
        tracer.record(
            correlation_id=correlation_id,
            stage=stage,
            event=event,
            payload_bytes=_payload_size_bytes(payload),
            latency_ms=(time.perf_counter() - start) * 1000.0,
        )
        record_latency((time.perf_counter() - start) * 1000.0)

    async def _isa_task() -> None:
        await _sleep_jitter(rng, jitter.isa)
        pkt = isa.ingest(source_text=business_case, repository_name=repo_root.name)
        _intercept("ISA", payload=pkt, event="INGEST")
        await q_isa_out.put(pkt)
        await q_isa_out.put(None)

    async def _auditor_task(
        *,
        auditor: TwinAuditor,
        schema_file: str,
        from_agent: str,
        to_agent: str,
        to_stage: str,
        q_in: asyncio.Queue[dict | None],
        q_out: asyncio.Queue[dict | None],
        jitter_bounds: tuple[float, float],
        event: str,
    ) -> None:
        while True:
            pkt = await q_in.get()
            if pkt is None:
                await q_out.put(None)
                return
            await _sleep_jitter(rng, jitter_bounds)
            auditor.sign_off(schema_file=schema_file, packet=pkt, from_agent=from_agent, to_agent=to_agent)
            _intercept(to_stage, payload=pkt, event=event)
            await q_out.put(pkt)

    async def _sas_task() -> None:
        while True:
            pkt = await q_sas_in.get()
            if pkt is None:
                await q_sas_out.put(None)
                return
            await _sleep_jitter(rng, jitter.sas)
            blueprint = sas.process(pkt)
            await q_sas_out.put(blueprint)

    async def _crs_task() -> None:
        while True:
            pkt = await q_crs_in.get()
            if pkt is None:
                await q_crs_out.put(None)
                return
            await _sleep_jitter(rng, jitter.crs)
            clearance = crs.assess(pkt)
            await q_crs_out.put(clearance)

    async def _boa_task() -> dict[str, Any]:
        pkt = await q_boa_in.get()
        if pkt is None:
            raise PipelineHaltException("BOA received no clearance packet")
        await _sleep_jitter(rng, jitter.boa)
        clearance = pkt.get("clearance") if isinstance(pkt, dict) else None
        build_ready = bool((clearance or {}).get("build_ready")) if isinstance(clearance, dict) else False
        if not build_ready:
            raise PipelineHaltException("CRS did not authorize build (build_ready=false)")
        return {
            "status": "built",
            "correlation_id": correlation_id,
        }

    tasks: list[asyncio.Task[Any]] = []
    try:
        tasks = [
            asyncio.create_task(_isa_task(), name="strain-isa"),
            asyncio.create_task(
                _auditor_task(
                    auditor=ita,
                    schema_file="intake_handshake.json",
                    from_agent="ISA",
                    to_agent="SAS",
                    to_stage="SAS",
                    q_in=q_isa_out,
                    q_out=q_sas_in,
                    jitter_bounds=jitter.ita,
                    event="HANDOFF_ISA_SAS",
                ),
                name="strain-ita",
            ),
            asyncio.create_task(_sas_task(), name="strain-sas"),
            asyncio.create_task(
                _auditor_task(
                    auditor=ata,
                    schema_file="architecture_blueprint.json",
                    from_agent="SAS",
                    to_agent="CRS",
                    to_stage="CRS",
                    q_in=q_sas_out,
                    q_out=q_crs_in,
                    jitter_bounds=jitter.ata,
                    event="HANDOFF_SAS_CRS",
                ),
                name="strain-ata",
            ),
            asyncio.create_task(_crs_task(), name="strain-crs"),
            asyncio.create_task(
                _auditor_task(
                    auditor=rta,
                    schema_file="risk_clearance.json",
                    from_agent="CRS",
                    to_agent="BOA",
                    to_stage="BOA",
                    q_in=q_crs_out,
                    q_out=q_boa_in,
                    jitter_bounds=jitter.rta,
                    event="HANDOFF_CRS_BOA",
                ),
                name="strain-rta",
            ),
        ]
        artifact_task = asyncio.create_task(_boa_task(), name="strain-boa")
        await asyncio.gather(*tasks)
        return await artifact_task
    finally:
        for t in tasks:
            t.cancel()


class TestTelemetryStrainRig(unittest.IsolatedAsyncioTestCase):
    """Asynchronous concurrency and jitter stress tests for telemetry + sequencing."""

    @classmethod
    def setUpClass(cls) -> None:
        # Make scheduling deterministic across runs when possible.
        random.seed(1337)

    async def asyncSetUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[1]
        self.logs_dir = self.repo_root / "logs"

        self._restore_text: dict[Path, str | None] = {}
        for path in (
            self.logs_dir / "CRITICAL_MISALIGNMENT.json",
            self.logs_dir / "TELEMETRY_TRACE.json",
        ):
            self._restore_text[path] = path.read_text(encoding="utf-8") if path.exists() else None

        self._logs_dir_existed = self.logs_dir.exists()

    async def asyncTearDown(self) -> None:
        for path, prior in self._restore_text.items():
            if prior is None:
                if path.exists():
                    path.unlink()
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(prior, encoding="utf-8")

        if not self._logs_dir_existed and self.logs_dir.exists():
            remaining = list(self.logs_dir.iterdir())
            if not remaining:
                self.logs_dir.rmdir()

    async def test_01_high_throughput_async_injection_suite(self) -> None:
        tracer = TelemetryTracer(logs_dir=self.logs_dir, capacity=1024)
        verifier = MatrixVerifier(logs_dir=self.logs_dir)

        latencies_ms: list[float] = []

        def _record_latency(v: float) -> None:
            latencies_ms.append(v)

        jitter = _JitterProfile()
        seed = 4242

        async def _pipeline_worker(idx: int) -> None:
            rng = random.Random(seed + idx)
            business_case = f"Telemetry Strain Rig business case {idx} ({uuid.uuid4()})"
            await asyncio.wait_for(
                _run_instrumented_handshake_once(
                    repo_root=self.repo_root,
                    logs_dir=self.logs_dir,
                    tracer=tracer,
                    verifier=verifier,
                    business_case=business_case,
                    rng=rng,
                    jitter=jitter,
                    record_latency=_record_latency,
                ),
                timeout=5.0,
            )

        async def _telemetry_flood_worker(idx: int) -> None:
            rng = random.Random(9000 + idx)
            cid = str(uuid.uuid4())
            for j in range(250):
                await _sleep_jitter(rng, (0.0, 0.0005))
                tracer.record(
                    correlation_id=cid,
                    stage="ISA",
                    event="FLOOD",
                    payload_bytes=64,
                    latency_ms=0.0,
                    metadata={"worker": idx, "seq": j},
                )

        async with asyncio.TaskGroup() as tg:
            for i in range(64):
                tg.create_task(_pipeline_worker(i))
            for i in range(60):
                tg.create_task(_telemetry_flood_worker(i))

        self.assertEqual(verifier.inflight(), 0, "Expected verifier inflight set to be empty after BOA completion")
        trace_path = tracer.flush_trace()
        trace = _load_json(trace_path)
        self.assertIsInstance(trace, list)
        self.assertLessEqual(len(trace), tracer.capacity)
        if trace:
            self.assertIn("signature", trace[-1])
            self.assertIn("sequence", trace[-1])

        # Micro-latency sanity check: telemetry interceptors should remain low overhead.
        if latencies_ms:
            self.assertLess(max(latencies_ms), 50.0, "Unexpected high latency from verifier+tracer interceptors")

        # Ensure no named strain tasks leaked.
        leaked = [t for t in asyncio.all_tasks() if not t.done() and (t.get_name() or "").startswith("strain-")]
        self.assertEqual(leaked, [], f"Leaked asyncio tasks: {[t.get_name() for t in leaked]}")

    async def test_02_race_condition_out_of_order_sequence_emulation(self) -> None:
        verifier = MatrixVerifier(logs_dir=self.logs_dir)
        correlation_id = str(uuid.uuid4())

        # Establish ISA stage, then intentionally attempt a BOA transition ahead of CRS.
        verifier.verify_transition(correlation_id=correlation_id, stage="ISA", payload={"event": "seed"})

        async def _early_boa() -> None:
            await asyncio.sleep(0.001)
            verifier.verify_transition(correlation_id=correlation_id, stage="BOA", payload={"event": "early"})

        with self.assertRaises(PipelineHaltException):
            await asyncio.gather(_early_boa())

        critical = self.logs_dir / "CRITICAL_MISALIGNMENT.json"
        self.assertTrue(critical.exists(), "Expected CRITICAL_MISALIGNMENT.json to be written on out-of-order DEAD_HALT")
        snapshot = _load_json(critical)
        self.assertEqual(snapshot.get("pipeline_state"), "DEAD_HALT")
        state = snapshot.get("state") or {}
        self.assertEqual(state.get("observed_stage"), "BOA")
        self.assertEqual(state.get("expected_stage"), "SAS")

    async def test_03_memory_boundary_ring_buffer_exhaustion(self) -> None:
        tracer = TelemetryTracer(logs_dir=self.logs_dir, capacity=128)
        cid = str(uuid.uuid4())

        for i in range(10_000):
            tracer.record(
                correlation_id=cid,
                stage="ISA",
                event="EXHAUST",
                payload_bytes=256,
                latency_ms=0.0,
                metadata={"i": i},
            )

        snapshot = tracer.snapshot()
        self.assertEqual(len(snapshot), 128)
        self.assertGreater(snapshot[0]["sequence"], 1, "Expected oldest records to be evicted under ring-buffer pressure")
        path = tracer.flush_trace()
        loaded = _load_json(path)
        self.assertIsInstance(loaded, list)
        self.assertEqual(len(loaded), 128)

    async def test_04_telemetry_backpressure_and_micro_latency_audit(self) -> None:
        tracer = TelemetryTracer(logs_dir=self.logs_dir, capacity=2048)
        verifier = MatrixVerifier(logs_dir=self.logs_dir)
        latencies_ms: list[float] = []

        def _record_latency(v: float) -> None:
            latencies_ms.append(v)

        jitter = _JitterProfile(isa=(0.0, 0.002), ita=(0.0, 0.002), sas=(0.0, 0.002), ata=(0.0, 0.002), crs=(0.0, 0.002), rta=(0.0, 0.002), boa=(0.0, 0.002))
        seed = 11_111

        async def _run_batch() -> None:
            async with asyncio.TaskGroup() as tg:
                for i in range(80):
                    rng = random.Random(seed + i)
                    business_case = f"Backpressure audit {i} ({uuid.uuid4()})"
                    tg.create_task(
                        _run_instrumented_handshake_once(
                            repo_root=self.repo_root,
                            logs_dir=self.logs_dir,
                            tracer=tracer,
                            verifier=verifier,
                            business_case=business_case,
                            rng=rng,
                            jitter=jitter,
                            record_latency=_record_latency,
                        )
                    )

        await asyncio.wait_for(_run_batch(), timeout=8.0)
        self.assertEqual(verifier.inflight(), 0)
        if latencies_ms:
            self.assertLess(max(latencies_ms), 50.0)
