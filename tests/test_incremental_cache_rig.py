import asyncio
import json
import shutil
import time
from pathlib import Path
import unittest

from agents.registry import AgentRegistry
from core.handshake import HandshakePipeline


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


class TestIncrementalCacheRig(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[1]
        self.logs_dir = self.repo_root / "logs"
        self.cache_root = self.repo_root / ".workspace_cache"
        self.schema_path = self.repo_root / "schema" / "intake_handshake.json"

        self._restore_text: dict[Path, str | None] = {}
        for path in (
            self.logs_dir / "BUILD_ARTIFACT.json",
            self.logs_dir / "CRITICAL_MISALIGNMENT.json",
            self.logs_dir / "TELEMETRY_TRACE.json",
            self.schema_path,
        ):
            self._restore_text[path] = path.read_text(encoding="utf-8") if path.exists() else None

        self._cache_existed = self.cache_root.exists()
        if self.cache_root.exists():
            shutil.rmtree(self.cache_root)

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

    async def _run_once(self, *, business_case: str) -> dict:
        registry = AgentRegistry(repo_root=self.repo_root, logs_dir=self.logs_dir)
        isa, sas, crs, boa = registry.build(repository_name=self.repo_root.name)
        pipeline = HandshakePipeline(schema_dir=self.repo_root / "schema", logs_dir=self.logs_dir)
        return await asyncio.wait_for(
            pipeline.run(
                isa=isa,
                sas=sas,
                crs=crs,
                boa=boa,
                source_text=business_case,
                repository_name=self.repo_root.name,
            ),
            timeout=5.0,
        )

    def _trace_records(self) -> list[dict]:
        path = self.logs_dir / "TELEMETRY_TRACE.json"
        self.assertTrue(path.exists(), "Expected logs/TELEMETRY_TRACE.json to be written")
        loaded = _load_json(path)
        self.assertIsInstance(loaded, list)
        return loaded  # type: ignore[return-value]

    async def test_01_incremental_cache_hit_miss_and_schema_invalidation(self) -> None:
        business_case = "Incremental cache rig business case: identical inputs should cache."

        t0 = time.perf_counter()
        artifact_1 = await self._run_once(business_case=business_case)
        wall_1 = time.perf_counter() - t0
        trace_1 = self._trace_records()

        misses_1 = [r for r in trace_1 if r.get("event") == "CACHE_MISS"]
        self.assertEqual(len(misses_1), 4)
        self.assertEqual({r.get("stage") for r in misses_1}, {"ISA", "SAS", "CRS", "BOA"})

        artifact_path = Path(str(artifact_1.get("artifact_path")))
        self.assertTrue(artifact_path.exists(), "Expected build artifact to exist after first run")
        artifact_bytes_1 = artifact_path.read_bytes()

        t1 = time.perf_counter()
        artifact_2 = await self._run_once(business_case=business_case)
        wall_2 = time.perf_counter() - t1
        trace_2 = self._trace_records()

        hits_2 = [r for r in trace_2 if r.get("event") == "CACHE_HIT"]
        self.assertEqual(len(hits_2), 4)
        self.assertEqual({r.get("stage") for r in hits_2}, {"ISA", "SAS", "CRS", "BOA"})
        self.assertEqual([r for r in trace_2 if r.get("event") == "CACHE_MISS"], [])

        self.assertLess(wall_2, max(0.05, wall_1 * 0.5))
        self.assertEqual(artifact_2.get("artifact_path"), artifact_1.get("artifact_path"))
        artifact_bytes_2 = artifact_path.read_bytes()
        self.assertEqual(len(artifact_bytes_2), len(artifact_bytes_1))
        self.assertEqual(artifact_bytes_2, artifact_bytes_1)

        # Mutate the handshake schema and ensure cache invalidates cleanly.
        original = self.schema_path.read_text(encoding="utf-8")
        mutated = original.replace("\n", "\n", 1) + "\n"
        self.schema_path.write_text(mutated, encoding="utf-8")

        artifact_3 = await self._run_once(business_case=business_case)
        trace_3 = self._trace_records()
        misses_3 = [r for r in trace_3 if r.get("event") == "CACHE_MISS"]
        self.assertGreaterEqual(len(misses_3), 1)
        self.assertIn("ISA", {r.get("stage") for r in misses_3})
        self.assertEqual(artifact_3.get("status"), "built")

