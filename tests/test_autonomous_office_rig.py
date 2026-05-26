import asyncio
import json
import logging
from pathlib import Path
import unittest

import run_autonomous_office
from agents.config_loader import load_agent_guide_configs
from agents.registry import AgentRegistry
from core.exceptions import PipelineHaltException, SchemaMismatchedException
from core.handshake import HandshakePipeline
from core.hashutil import fnv1a_32
from core.matrix_verifier import GovernancePolicy, MatrixVerifier
from core.telemetry import TelemetryTracker


def _is_hex32(token: object) -> bool:
    if not isinstance(token, str) or len(token) != 8:
        return False
    for ch in token:
        if ch not in "0123456789abcdefABCDEF":
            return False
    return True


def _canonical_packet(packet: dict) -> str:
    canonical_packet = packet
    if "handshake_hash" in packet:
        canonical_packet = dict(packet)
        canonical_packet.pop("handshake_hash", None)
    return json.dumps(canonical_packet, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _expected_handshake_hash(from_agent: str, to_agent: str, schema_file: str, packet: dict) -> str:
    canonical = _canonical_packet(packet)
    return fnv1a_32(f"{from_agent}->{to_agent}:{schema_file}:{canonical}")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class TestAutonomousOfficeRig(unittest.IsolatedAsyncioTestCase):
    _layer_results: dict[str, bool] = {
        "happy_path_integration": False,
        "schema_constraint_mutation": False,
        "state_corruption_bypass": False,
        "markdown_parsing_resilience": False,
    }

    @classmethod
    def setUpClass(cls) -> None:
        run_autonomous_office.configure_logging()
        logging.getLogger("asyncio").setLevel(logging.WARNING)

    @classmethod
    def tearDownClass(cls) -> None:
        executed = [name for name, ok in cls._layer_results.items() if ok]
        total = len(cls._layer_results)
        completed = len(executed)
        percent = int((completed / total) * 100) if total else 100
        print(
            json.dumps(
                {
                    "rig": "tests/test_autonomous_office_rig.py",
                    "layers_total": total,
                    "layers_executed": executed,
                    "layer_coverage_percent": percent,
                    "validation_matrix": cls._layer_results,
                },
                sort_keys=True,
                ensure_ascii=False,
            )
        )

    async def asyncSetUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[1]
        self.logs_dir = self.repo_root / "logs"

        self._restore_text: dict[Path, str | None] = {}
        for path in (
            self.repo_root / "OFFICE_INTAKE.json",
            self.repo_root / "AGENT_GUIDE_LIST.md",
            self.logs_dir / "BUILD_ARTIFACT.json",
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

    async def test_01_happy_path_integration_vector(self) -> None:
        source_text = "\n".join(
            [
                "Initialize autonomous office runtime core for REMOTE-AGENTS.",
                "- Validate deterministic handshake signing",
                "- Produce build artifact",
            ]
        )
        (self.repo_root / "OFFICE_INTAKE.json").write_text(
            json.dumps({"source_text": source_text, "repository_name": "REMOTE-AGENTS"}, sort_keys=True, ensure_ascii=False)
            + "\n",
            encoding="utf-8",
        )

        rc = await run_autonomous_office._amain()
        self.assertEqual(rc, 0)

        artifact_path = self.logs_dir / "BUILD_ARTIFACT.json"
        self.assertTrue(artifact_path.exists(), "Expected logs/BUILD_ARTIFACT.json to be created")
        artifact = _load_json(artifact_path)
        self.assertEqual(artifact.get("status"), "built")

        telemetry = artifact.get("telemetry")
        self.assertIsInstance(telemetry, list)
        self.assertEqual(len(telemetry), 3)

        trace_path = self.logs_dir / "TELEMETRY_TRACE.json"
        self.assertTrue(trace_path.exists(), "Expected logs/TELEMETRY_TRACE.json to be written after a successful build")
        trace = _load_json(trace_path)
        self.assertEqual(trace.get("allowed_path"), ["ISA", "SAS", "CRS", "BOA"])
        self.assertEqual(
            trace.get("audited_path"),
            [{"from": "ISA", "to": "SAS"}, {"from": "SAS", "to": "CRS"}, {"from": "CRS", "to": "BOA"}],
        )
        self.assertEqual(trace.get("handshake_telemetry"), telemetry)
        micro_log = trace.get("micro_log")
        self.assertIsInstance(micro_log, list)
        self.assertTrue(micro_log, "Expected micro_log to contain at least one event")
        for idx, event in enumerate(micro_log[:10]):
            self.assertIsInstance(event, dict, f"micro_log[{idx}] must be an object")
            for key in ("component", "twin_hash", "event_type", "latency_ms"):
                self.assertIn(key, event, f"micro_log[{idx}] missing key {key!r}")

        registry = AgentRegistry(repo_root=self.repo_root, logs_dir=self.logs_dir)
        isa, sas, crs, _boa = registry.build(repository_name="REMOTE-AGENTS")
        intake_packet = isa.ingest(source_text=source_text, repository_name="REMOTE-AGENTS")
        blueprint_packet = sas.process(intake_packet)
        clearance_packet = crs.assess(blueprint_packet)

        expected = [
            {
                "from": "ISA",
                "to": "SAS",
                "schema": "intake_handshake.json",
                "handshake_hash": _expected_handshake_hash("ISA", "SAS", "intake_handshake.json", intake_packet),
            },
            {
                "from": "SAS",
                "to": "CRS",
                "schema": "architecture_blueprint.json",
                "handshake_hash": _expected_handshake_hash("SAS", "CRS", "architecture_blueprint.json", blueprint_packet),
            },
            {
                "from": "CRS",
                "to": "BOA",
                "schema": "risk_clearance.json",
                "handshake_hash": _expected_handshake_hash("CRS", "BOA", "risk_clearance.json", clearance_packet),
            },
        ]

        for idx, row in enumerate(expected):
            self.assertEqual(telemetry[idx].get("from"), row["from"])
            self.assertEqual(telemetry[idx].get("to"), row["to"])
            self.assertEqual(telemetry[idx].get("schema"), row["schema"])
            token = telemetry[idx].get("handshake_hash")
            self.assertTrue(_is_hex32(token), f"Invalid FNV-1a signature token at telemetry[{idx}]")
            self.assertEqual(token, row["handshake_hash"])

        self.__class__._layer_results["happy_path_integration"] = True

    async def test_02_schema_constraint_mutation_chaos_layer_1(self) -> None:
        source_text = "Chaos layer 1: schema constraint mutation"

        registry = AgentRegistry(repo_root=self.repo_root, logs_dir=self.logs_dir)
        isa, sas, crs, boa = registry.build(repository_name="REMOTE-AGENTS")

        class CorruptISA:
            def ingest(self, source_text: str, repository_name: str | None = None) -> dict:
                pkt = isa.ingest(source_text=source_text, repository_name=repository_name)
                (pkt.get("payload") or {}).pop("request_id", None)
                return pkt

        pipeline = HandshakePipeline(schema_dir=self.repo_root / "schema", logs_dir=self.logs_dir)
        with self.assertRaises(SchemaMismatchedException):
            await pipeline.run(isa=CorruptISA(), sas=sas, crs=crs, boa=boa, source_text=source_text, repository_name="REMOTE-AGENTS")

        critical = self.logs_dir / "CRITICAL_MISALIGNMENT.json"
        self.assertTrue(critical.exists(), "Expected CRITICAL_MISALIGNMENT.json to be written on DEAD_HALT")
        snapshot = _load_json(critical)
        self.assertEqual(snapshot.get("pipeline_state"), "DEAD_HALT")

        state = snapshot.get("state") or {}
        self.assertEqual(state.get("pipeline_state"), "DEAD_HALT")
        self.__class__._layer_results["schema_constraint_mutation"] = True

    async def test_03_state_corruption_network_bypass_mutation_chaos_layer_2(self) -> None:
        source_text = "Chaos layer 2: corrupted handshake token injection"

        registry = AgentRegistry(repo_root=self.repo_root, logs_dir=self.logs_dir)
        isa, sas, crs, boa = registry.build(repository_name="REMOTE-AGENTS")

        class TamperISA:
            def ingest(self, source_text: str, repository_name: str | None = None) -> dict:
                pkt = isa.ingest(source_text=source_text, repository_name=repository_name)
                pkt["handshake_hash"] = "deadbeef"
                return pkt

        pipeline = HandshakePipeline(schema_dir=self.repo_root / "schema", logs_dir=self.logs_dir)
        with self.assertRaises(PipelineHaltException):
            await pipeline.run(isa=TamperISA(), sas=sas, crs=crs, boa=boa, source_text=source_text, repository_name="REMOTE-AGENTS")

        critical = self.logs_dir / "CRITICAL_MISALIGNMENT.json"
        self.assertTrue(critical.exists(), "Expected CRITICAL_MISALIGNMENT.json to be written on DEAD_HALT")
        snapshot = _load_json(critical)
        self.assertEqual(snapshot.get("pipeline_state"), "DEAD_HALT")
        self.assertIn("Handshake hash mismatch", snapshot.get("error", ""))

        state = snapshot.get("state") or {}
        self.assertEqual(state.get("pipeline_state"), "DEAD_HALT")
        self.__class__._layer_results["state_corruption_bypass"] = True

    async def test_04_environmental_resilience_markdown_parsing_rig(self) -> None:
        guide_path = self.repo_root / "AGENT_GUIDE_LIST.md"
        logs_dir_pre = self.logs_dir.exists()

        guide_path.write_text(
            "\n".join(
                [
                    "# Corrupted Agent Guide List",
                    "",
                    "* **JSON Configuration:** `{\"repository_name\":\"REMOTE-AGENTS\",\"detected_class\":\"rig\"}`",
                    "* **JSON Configuration:** `{\"repository_name\":\"BROKEN\",\"detected_class\":`",
                    "* **JSON Configuration:** `{not-json}`",
                    "* **JSON Configuration:** `N/A`",
                    "",
                    "Trailing content should remain parseable.",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        configs = load_agent_guide_configs(guide_path)
        self.assertIn("REMOTE-AGENTS", configs)
        self.assertEqual(configs["REMOTE-AGENTS"].get("detected_class"), "rig")
        self.assertNotIn("BROKEN", configs)

        registry = AgentRegistry(repo_root=self.repo_root, logs_dir=self.logs_dir)
        registry.build(repository_name="REMOTE-AGENTS")

        self.assertEqual(self.logs_dir.exists(), logs_dir_pre, "Config parsing must not mutate filesystem state")
        self.__class__._layer_results["markdown_parsing_resilience"] = True

    async def test_05_governance_lookahead_violation_halts_pipeline(self) -> None:
        source_text = "Governance: lookahead violation should halt pipeline"

        registry = AgentRegistry(repo_root=self.repo_root, logs_dir=self.logs_dir)
        isa, sas, crs, boa = registry.build(repository_name="REMOTE-AGENTS")

        policy = GovernancePolicy(allowed_path=("ISA", "SAS", "BOA"), source_path="tests/test_autonomous_office_rig.py")
        verifier = MatrixVerifier(policy)
        telemetry = TelemetryTracker(max_events=256)

        pipeline = HandshakePipeline(schema_dir=self.repo_root / "schema", logs_dir=self.logs_dir)
        with self.assertRaises(PipelineHaltException):
            await pipeline.run(
                isa=isa,
                sas=sas,
                crs=crs,
                boa=boa,
                source_text=source_text,
                repository_name="REMOTE-AGENTS",
                telemetry_tracker=telemetry,
                verifier=verifier,
            )

        critical = self.logs_dir / "CRITICAL_MISALIGNMENT.json"
        self.assertTrue(critical.exists(), "Expected CRITICAL_MISALIGNMENT.json to be written on DEAD_HALT")
        snapshot = _load_json(critical)
        state = snapshot.get("state") or {}
        rows = state.get("telemetry") or []
        self.assertEqual(len(rows), 1, "Out-of-sequence hop must bypass normal telemetry append")
        self.assertFalse((self.logs_dir / "TELEMETRY_TRACE.json").exists(), "Telemetry trace should only be written after a valid build")
        micro_log = state.get("micro_log")
        self.assertIsInstance(micro_log, list)


if __name__ == "__main__":
    unittest.main(verbosity=2)
