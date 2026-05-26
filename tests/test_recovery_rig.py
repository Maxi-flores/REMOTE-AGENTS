from __future__ import annotations

import asyncio
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import run_autonomous_office
from core.handshake import PacketEnvelope
from core.types import JSONObject
from agents.risk_compliance import RiskCompliance


class TestRecoveryRig(unittest.IsolatedAsyncioTestCase):
    async def test_checkpoint_resume_skips_upstream_agents(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        business_case = "\n".join(
            [
                "Recovery rig business case: simulate mid-flight crash.",
                "- Ensure architecture stage is checkpointed",
                "- Resume runs only risk and build stages",
            ]
        )

        with TemporaryDirectory() as tmp:
            log_dir = Path(tmp) / "logs"
            argv = [
                "--business-case",
                business_case,
                "--repo-root",
                str(repo_root),
                "--log-dir",
                str(log_dir),
            ]

            async def _crash_risk(
                self: RiskCompliance, *, architecture_envelope: PacketEnvelope[JSONObject]
            ) -> JSONObject:
                await asyncio.sleep(0)
                raise RuntimeError("simulated crash during Architecture -> Risk transition")

            with patch.object(RiskCompliance, "build_risk_payload", new=_crash_risk):
                rc1 = await asyncio.to_thread(run_autonomous_office.main, argv)

            self.assertEqual(rc1, 1)

            checkpoint_path = log_dir / "checkpoint_state.json"
            self.assertTrue(checkpoint_path.exists(), "Expected checkpoint_state.json to be created")
            checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            self.assertEqual(checkpoint.get("active_stage"), "architecture_to_risk")
            payload = checkpoint.get("payload") or {}
            self.assertIsInstance(payload, dict)
            self.assertIn("architecture_plan", payload)

            gov_path = log_dir / "governance.jsonl"
            self.assertTrue(gov_path.exists(), "Expected governance.jsonl to be created")
            before = gov_path.read_text(encoding="utf-8", errors="replace").splitlines()

            rc2 = await asyncio.to_thread(run_autonomous_office.main, argv)
            self.assertEqual(rc2, 0)

            after = gov_path.read_text(encoding="utf-8", errors="replace").splitlines()
            appended = after[len(before) :]

            appended_events: list[str] = []
            appended_states: list[str] = []
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
                if event == "STATE" and isinstance(obj.get("state"), str):
                    appended_states.append(obj["state"])

            self.assertNotIn("INTAKE_COMPLETE", appended_events)
            self.assertNotIn("ARCHITECTURE_COMPLETE", appended_events)
            self.assertIn("RISK_COMPLETE", appended_events)
            self.assertIn("BUILD_EXECUTION", appended_events)
            self.assertIn("Completed", appended_states)


if __name__ == "__main__":
    unittest.main(verbosity=2)
