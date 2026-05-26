import asyncio
import json
import logging
from pathlib import Path

from .exceptions import PipelineHaltException
from .fault import dump_critical_misalignment
from .hashutil import fnv1a_32
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

    async def run(self, isa, sas, crs, boa, source_text: str, repository_name: str | None = None) -> dict:
        state: dict = {"pipeline_state": "RUNNING", "telemetry": []}

        q_isa_out: asyncio.Queue = asyncio.Queue()
        q_sas_in: asyncio.Queue = asyncio.Queue()
        q_sas_out: asyncio.Queue = asyncio.Queue()
        q_crs_in: asyncio.Queue = asyncio.Queue()
        q_crs_out: asyncio.Queue = asyncio.Queue()
        q_boa_in: asyncio.Queue = asyncio.Queue()

        ita = TwinAuditor("ITA", self._validator, self._logs_dir)
        ata = TwinAuditor("ATA", self._validator, self._logs_dir)
        rta = TwinAuditor("RTA", self._validator, self._logs_dir)

        async def _isa_task() -> None:
            packet = isa.ingest(source_text=source_text, repository_name=repository_name)
            state["isa_packet"] = packet
            await q_isa_out.put(packet)
            await q_isa_out.put(None)

        async def _auditor_task(
            auditor: TwinAuditor,
            schema_file: str,
            from_agent: str,
            to_agent: str,
            q_in: asyncio.Queue,
            q_out: asyncio.Queue,
        ) -> None:
            while True:
                pkt = await q_in.get()
                if pkt is None:
                    await q_out.put(None)
                    return
                handshake_hash = auditor.sign_off(schema_file=schema_file, packet=pkt, from_agent=from_agent, to_agent=to_agent)
                state["telemetry"].append(
                    {"from": from_agent, "to": to_agent, "schema": schema_file, "handshake_hash": handshake_hash}
                )
                await q_out.put(pkt)

        async def _sas_task() -> None:
            while True:
                pkt = await q_sas_in.get()
                if pkt is None:
                    await q_sas_out.put(None)
                    return
                blueprint = sas.process(pkt)
                state["sas_packet"] = blueprint
                await q_sas_out.put(blueprint)

        async def _crs_task() -> None:
            while True:
                pkt = await q_crs_in.get()
                if pkt is None:
                    await q_crs_out.put(None)
                    return
                clearance = crs.assess(pkt)
                state["crs_packet"] = clearance
                await q_crs_out.put(clearance)

        async def _boa_task() -> dict:
            while True:
                pkt = await q_boa_in.get()
                if pkt is None:
                    raise PipelineHaltException("BOA received no clearance packet")
                artifact = boa.build(pkt, telemetry=state.get("telemetry", []))
                state["pipeline_state"] = "COMPLETED"
                state["artifact"] = artifact
                return artifact

        try:
            tasks = [
                asyncio.create_task(_isa_task()),
                asyncio.create_task(_auditor_task(ita, "intake_handshake.json", "ISA", "SAS", q_isa_out, q_sas_in)),
                asyncio.create_task(_sas_task()),
                asyncio.create_task(_auditor_task(ata, "architecture_blueprint.json", "SAS", "CRS", q_sas_out, q_crs_in)),
                asyncio.create_task(_crs_task()),
                asyncio.create_task(_auditor_task(rta, "risk_clearance.json", "CRS", "BOA", q_crs_out, q_boa_in)),
            ]
            artifact_task = asyncio.create_task(_boa_task())
            await asyncio.gather(*tasks)
            return await artifact_task
        except Exception as exc:
            state["pipeline_state"] = "DEAD_HALT"
            dump_critical_misalignment(self._logs_dir, state, exc)
            raise
