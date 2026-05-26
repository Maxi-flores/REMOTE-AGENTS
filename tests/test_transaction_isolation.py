import asyncio
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import run_autonomous_office
from agents.software_architect import SoftwareArchitect


class TestWorkspaceTransactionIsolation(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[1]
        self.test_path = self.repo_root / "TRANSACTION_TEST.txt"
        self._prior_text: str | None = self.test_path.read_text(encoding="utf-8") if self.test_path.exists() else None
        self.test_path.write_text("original\n", encoding="utf-8")

    async def asyncTearDown(self) -> None:
        if self._prior_text is None:
            try:
                self.test_path.unlink(missing_ok=True)
            except OSError:
                pass
        else:
            self.test_path.write_text(self._prior_text, encoding="utf-8")

    async def test_crash_during_sas_write_rolls_back_workspace(self) -> None:
        business_case = "\n".join(
            [
                "Workspace transaction rig: simulate mid-SAS crash during file generation.",
                "- SAS will attempt to modify TRANSACTION_TEST.txt",
                "- Crash before checkpointing SAS stage",
                "- Resume must not corrupt workspace",
            ]
        )

        with TemporaryDirectory() as tmp:
            log_dir = Path(tmp) / "logs"
            argv = [
                "--business-case",
                business_case,
                "--repo-root",
                str(self.repo_root),
                "--log-dir",
                str(log_dir),
            ]

            original_impl = SoftwareArchitect.build_architecture_payload
            calls = 0

            async def _patched(self: SoftwareArchitect, *, intake_envelope):  # type: ignore[no-untyped-def]
                nonlocal calls
                if calls == 0:
                    calls += 1
                    with open(self.workspace.repo_root / "TRANSACTION_TEST.txt", "w", encoding="utf-8") as f:
                        f.write("partial\n")
                        f.flush()
                    raise RuntimeError("simulated crash during SAS file generation")

                with open(self.workspace.repo_root / "TRANSACTION_TEST.txt", "w", encoding="utf-8") as f:
                    f.write("committed\n")
                    f.flush()
                return await original_impl(self, intake_envelope=intake_envelope)

            with patch.object(SoftwareArchitect, "build_architecture_payload", new=_patched):
                rc1 = await asyncio.to_thread(run_autonomous_office.main, argv)

            self.assertEqual(rc1, 1)
            self.assertEqual(self.test_path.read_text(encoding="utf-8"), "original\n")

            checkpoint_path = log_dir / "checkpoint_state.json"
            self.assertTrue(checkpoint_path.exists(), "Expected checkpoint_state.json to be created")
            checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            self.assertEqual(checkpoint.get("active_stage"), "intake_to_architecture")
            token = checkpoint.get("execution_token")
            self.assertIsInstance(token, str)
            staging_token_dir = self.repo_root / ".workspace_staging" / token
            self.assertFalse(staging_token_dir.exists(), "Expected SAS staging delta to be discarded on crash")

            gov_path = log_dir / "governance.jsonl"
            self.assertTrue(gov_path.exists(), "Expected governance.jsonl to be created")
            before = gov_path.read_text(encoding="utf-8", errors="replace").splitlines()

            with patch.object(SoftwareArchitect, "build_architecture_payload", new=_patched):
                rc2 = await asyncio.to_thread(run_autonomous_office.main, argv + ["--resolve-intervention"])

            self.assertEqual(rc2, 0)
            self.assertEqual(self.test_path.read_text(encoding="utf-8"), "committed\n")
            self.assertFalse(staging_token_dir.exists(), "Expected workspace staging to be cleaned after successful run")

            after = gov_path.read_text(encoding="utf-8", errors="replace").splitlines()
            appended = after[len(before) :]

            appended_events: list[str] = []
            for ln in appended:
                try:
                    obj = json.loads(ln)
                except Exception:
                    continue
                if not isinstance(obj, dict):
                    continue
                event = obj.get("event")
                if isinstance(event, str):
                    appended_events.append(event)

            self.assertNotIn("INTAKE_COMPLETE", appended_events)
            self.assertIn("ARCHITECTURE_COMPLETE", appended_events)


if __name__ == "__main__":
    unittest.main(verbosity=2)

