import asyncio
import json
import logging
import time
from pathlib import Path

from .exceptions import PipelineHaltException
from .fault import dump_critical_misalignment
from .hashutil import fnv1a_32
from .matrix_verifier import MatrixVerifier
from .telemetry import TelemetryTracker, estimate_payload_bytes
from .validator import SchemaValidator


class TwinAuditor:
    def __init__(self, name: str, validator: SchemaValidator, logs_dir: Path) -> None:
        self._name = name
        self._validator = validator
        self._logs_dir = logs_dir
        self._log = logging.getLogger(name)

    def sign_off(self, schema_file: str, packet: dict, from_agent: str, to_agent: str) -> str:
        self._validator.validate(schema_file, packet)
        provided_hash = packet.get("handshake_hash")
        canonical_packet = packet
        if "handshake_hash" in packet:
            canonical_packet = dict(packet)
            canonical_packet.pop("handshake_hash", None)
        canonical = json.dumps(canonical_packet, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        handshake_hash = fnv1a_32(f"{from_agent}->{to_agent}:{schema_file}:{canonical}")
        if provided_hash is not None:
            if not isinstance(provided_hash, str) or provided_hash != handshake_hash:
                raise PipelineHaltException(
                    f"Handshake hash mismatch for {from_agent}->{to_agent} ({schema_file}): "
                    f"provided={provided_hash!r} expected={handshake_hash!r}"
                )
        self._log.info(
            "Twin-to-Twin Handshake Validated (%s -> %s, %s)",
            from_agent,
            to_agent,
            schema_file,
            extra={"component": self._name, "handshake_hash": handshake_hash},
        )
        return handshake_hash


class HandshakePipeline:
    def __init__(self, schema_dir: Path, logs_dir: Path) -> None:
        self._schema_dir = schema_dir
        self._logs_dir = logs_dir
        self._validator = SchemaValidator(schema_dir)

    async def run(
        self,
        isa,
        sas,
        crs,
        boa,
        source_text: str,
        repository_name: str | None = None,
        *,
        telemetry_tracker: TelemetryTracker | None = None,
        verifier: MatrixVerifier | None = None,
    ) -> dict:
        state: dict = {"pipeline_state": "RUNNING", "telemetry": []}

        tasks: list[asyncio.Task] = []
        artifact_task: asyncio.Task | None = None

        q_isa_out: asyncio.Queue = asyncio.Queue()
        q_sas_in: asyncio.Queue = asyncio.Queue()
        q_sas_out: asyncio.Queue = asyncio.Queue()
        q_crs_in: asyncio.Queue = asyncio.Queue()
        q_crs_out: asyncio.Queue = asyncio.Queue()
        q_boa_in: asyncio.Queue = asyncio.Queue()

        ita = TwinAuditor("ITA", self._validator, self._logs_dir)
        ata = TwinAuditor("ATA", self._validator, self._logs_dir)
        rta = TwinAuditor("RTA", self._validator, self._logs_dir)
        verifier_lock = asyncio.Lock()

        async def _isa_task() -> None:
            packet = isa.ingest(source_text=source_text, repository_name=repository_name)
            state["isa_packet"] = packet
            if telemetry_tracker is not None:
                await telemetry_tracker.record(
                    component="ISA",
                    event_type="agent_emit",
                    twin_hash="-",
                    latency_ms=0.0,
                    src_agent="ISA",
                    dst_agent="SAS",
                    payload_bytes=estimate_payload_bytes(packet),
                )
                await telemetry_tracker.mark_enqueue(queue_name="q_isa_out", item=packet, src_agent="ISA", dst_agent="SAS")
            await q_isa_out.put(packet)
            await q_isa_out.put(None)

        async def _auditor_task(
            auditor: TwinAuditor,
            schema_file: str,
            from_agent: str,
            to_agent: str,
            q_in_name: str,
            q_out_name: str,
            q_in: asyncio.Queue,
            q_out: asyncio.Queue,
        ) -> None:
            while True:
                pkt = await q_in.get()
                if pkt is None:
                    await q_out.put(None)
                    return
                if telemetry_tracker is not None:
                    wait_ms, mark = await telemetry_tracker.pop_enqueue_latency_ms(queue_name=q_in_name, item=pkt)
                    if wait_ms is not None:
                        await telemetry_tracker.record(
                            component="HandshakePipeline",
                            event_type="queue_wait",
                            twin_hash="-",
                            latency_ms=wait_ms,
                            src_agent=mark.src_agent if mark else None,
                            dst_agent=mark.dst_agent if mark else None,
                            payload_bytes=estimate_payload_bytes(pkt),
                            extra={"queue_name": q_in_name},
                        )
                if verifier is not None:
                    async with verifier_lock:
                        verifier.verify_transition(from_agent=from_agent, to_agent=to_agent)
                start = time.monotonic()
                handshake_hash = auditor.sign_off(schema_file=schema_file, packet=pkt, from_agent=from_agent, to_agent=to_agent)
                end = time.monotonic()
                if verifier is not None:
                    async with verifier_lock:
                        verifier.verify_twin_hash(handshake_hash, context=f"{from_agent}->{to_agent}:{schema_file}")
                if telemetry_tracker is not None:
                    await telemetry_tracker.record(
                        component=auditor._name,
                        event_type="state_transition",
                        twin_hash=handshake_hash,
                        latency_ms=(end - start) * 1000.0,
                        src_agent=from_agent,
                        dst_agent=to_agent,
                        payload_bytes=estimate_payload_bytes(pkt),
                        extra={"schema": schema_file},
                    )
                state["telemetry"].append(
                    {"from": from_agent, "to": to_agent, "schema": schema_file, "handshake_hash": handshake_hash}
                )
                if telemetry_tracker is not None:
                    await telemetry_tracker.mark_enqueue(queue_name=q_out_name, item=pkt, src_agent=from_agent, dst_agent=to_agent)
                await q_out.put(pkt)

        async def _sas_task() -> None:
            while True:
                pkt = await q_sas_in.get()
                if pkt is None:
                    await q_sas_out.put(None)
                    return
                if telemetry_tracker is not None:
                    wait_ms, mark = await telemetry_tracker.pop_enqueue_latency_ms(queue_name="q_sas_in", item=pkt)
                    if wait_ms is not None:
                        await telemetry_tracker.record(
                            component="HandshakePipeline",
                            event_type="queue_wait",
                            twin_hash="-",
                            latency_ms=wait_ms,
                            src_agent=mark.src_agent if mark else None,
                            dst_agent=mark.dst_agent if mark else None,
                            payload_bytes=estimate_payload_bytes(pkt),
                            extra={"queue_name": "q_sas_in"},
                        )
                start = time.monotonic()
                blueprint = sas.process(pkt)
                end = time.monotonic()
                state["sas_packet"] = blueprint
                if telemetry_tracker is not None:
                    await telemetry_tracker.record(
                        component="SAS",
                        event_type="agent_process",
                        twin_hash="-",
                        latency_ms=(end - start) * 1000.0,
                        src_agent="SAS",
                        dst_agent="CRS",
                        payload_bytes=estimate_payload_bytes(blueprint),
                    )
                    await telemetry_tracker.mark_enqueue(queue_name="q_sas_out", item=blueprint, src_agent="SAS", dst_agent="CRS")
                await q_sas_out.put(blueprint)

        async def _crs_task() -> None:
            while True:
                pkt = await q_crs_in.get()
                if pkt is None:
                    await q_crs_out.put(None)
                    return
                if telemetry_tracker is not None:
                    wait_ms, mark = await telemetry_tracker.pop_enqueue_latency_ms(queue_name="q_crs_in", item=pkt)
                    if wait_ms is not None:
                        await telemetry_tracker.record(
                            component="HandshakePipeline",
                            event_type="queue_wait",
                            twin_hash="-",
                            latency_ms=wait_ms,
                            src_agent=mark.src_agent if mark else None,
                            dst_agent=mark.dst_agent if mark else None,
                            payload_bytes=estimate_payload_bytes(pkt),
                            extra={"queue_name": "q_crs_in"},
                        )
                start = time.monotonic()
                clearance = crs.assess(pkt)
                end = time.monotonic()
                state["crs_packet"] = clearance
                if telemetry_tracker is not None:
                    await telemetry_tracker.record(
                        component="CRS",
                        event_type="agent_process",
                        twin_hash="-",
                        latency_ms=(end - start) * 1000.0,
                        src_agent="CRS",
                        dst_agent="BOA",
                        payload_bytes=estimate_payload_bytes(clearance),
                    )
                    await telemetry_tracker.mark_enqueue(queue_name="q_crs_out", item=clearance, src_agent="CRS", dst_agent="BOA")
                await q_crs_out.put(clearance)

        async def _boa_task() -> dict:
            while True:
                pkt = await q_boa_in.get()
                if pkt is None:
                    raise PipelineHaltException("BOA received no clearance packet")
                if telemetry_tracker is not None:
                    wait_ms, mark = await telemetry_tracker.pop_enqueue_latency_ms(queue_name="q_boa_in", item=pkt)
                    if wait_ms is not None:
                        await telemetry_tracker.record(
                            component="HandshakePipeline",
                            event_type="queue_wait",
                            twin_hash="-",
                            latency_ms=wait_ms,
                            src_agent=mark.src_agent if mark else None,
                            dst_agent=mark.dst_agent if mark else None,
                            payload_bytes=estimate_payload_bytes(pkt),
                            extra={"queue_name": "q_boa_in"},
                        )
                start = time.monotonic()
                artifact = boa.build(pkt, telemetry=state.get("telemetry", []))
                end = time.monotonic()
                state["pipeline_state"] = "COMPLETED"
                state["artifact"] = artifact
                if telemetry_tracker is not None:
                    await telemetry_tracker.record(
                        component="BOA",
                        event_type="build_artifact",
                        twin_hash="-",
                        latency_ms=(end - start) * 1000.0,
                        src_agent="CRS",
                        dst_agent="BOA",
                        payload_bytes=estimate_payload_bytes(artifact),
                        extra={"artifact_path": artifact.get("artifact_path")},
                    )
                return artifact

        try:
            tasks = [
                asyncio.create_task(_isa_task()),
                asyncio.create_task(_auditor_task(ita, "intake_handshake.json", "ISA", "SAS", "q_isa_out", "q_sas_in", q_isa_out, q_sas_in)),
                asyncio.create_task(_sas_task()),
                asyncio.create_task(_auditor_task(ata, "architecture_blueprint.json", "SAS", "CRS", "q_sas_out", "q_crs_in", q_sas_out, q_crs_in)),
                asyncio.create_task(_crs_task()),
                asyncio.create_task(_auditor_task(rta, "risk_clearance.json", "CRS", "BOA", "q_crs_out", "q_boa_in", q_crs_out, q_boa_in)),
            ]
            artifact_task = asyncio.create_task(_boa_task())
            await asyncio.gather(*tasks)
            artifact = await artifact_task
            if telemetry_tracker is not None:
                await telemetry_tracker.record(component="HandshakePipeline", event_type="pipeline_completed", twin_hash="-", latency_ms=0.0)
            if verifier is not None:
                try:
                    artifact_path_raw = artifact.get("artifact_path")
                    build_artifact_path = (
                        Path(artifact_path_raw) if isinstance(artifact_path_raw, str) else (self._logs_dir / "BUILD_ARTIFACT.json")
                    )
                    micro_log = await telemetry_tracker.snapshot() if telemetry_tracker is not None else []
                    verifier.write_telemetry_trace(
                        logs_dir=self._logs_dir,
                        build_artifact_path=build_artifact_path,
                        micro_log_events=micro_log,
                        handshake_telemetry=state.get("telemetry", []),
                        repository_name=repository_name,
                    )
                except Exception as tele_exc:
                    if telemetry_tracker is not None:
                        await telemetry_tracker.record(
                            component="HandshakePipeline",
                            event_type="telemetry_write_failed",
                            twin_hash="-",
                            latency_ms=0.0,
                            extra={"error": repr(tele_exc)},
                        )
            return artifact
        except Exception as exc:
            state["pipeline_state"] = "DEAD_HALT"
            for task in tasks:
                task.cancel()
            if artifact_task is not None:
                artifact_task.cancel()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            if artifact_task is not None:
                await asyncio.gather(artifact_task, return_exceptions=True)
            if telemetry_tracker is not None:
                await telemetry_tracker.record(
                    component="HandshakePipeline",
                    event_type="pipeline_error",
                    twin_hash="-",
                    latency_ms=0.0,
                    extra={"error": repr(exc)},
                )
                state["micro_log"] = await telemetry_tracker.snapshot()
            dump_critical_misalignment(self._logs_dir, state, exc)
            raise
