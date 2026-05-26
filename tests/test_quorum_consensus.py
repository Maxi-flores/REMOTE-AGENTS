import asyncio
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import run_autonomous_office
from core.governance import GovernanceLogger
from core.handshake import run_three_stage_pipeline
from core.recovery import CheckpointManager
from core.types import JSONObject
from core.exceptions import QuorumDissentException
from agents.software_architect import SoftwareArchitect


class _StubIntakeAgent:
    async def build_intake_payload(self, *, business_case: str, workspace_snapshot: JSONObject) -> JSONObject:
        # Intake stage does not write; it provides deterministic seed material.
        return {
            "business_case": business_case,
            "target_repositories": ["DEMO_REPO"],
            "requirements": ["req-a", "req-b"],
            "workspace_snapshot": workspace_snapshot,
        }


class _StubArchitectAgent:
    def __init__(self, repo_root: Path) -> None:
        self._repo_root = repo_root

    async def build_architecture_payload(self, *, intake_envelope) -> JSONObject:  # type: ignore[no-untyped-def]
        path = self._repo_root / "QUORUM_HAPPY.txt"
        with open(path, "w", encoding="utf-8") as f:
            f.write("architect\n")
        return {
            "target_repositories": ["DEMO_REPO"],
            "architecture_plan": ["step-1", "step-2"],
            "impact_assessment": {"notes": "ok"},
            "trace": {"intake_signature": intake_envelope.signature},
        }


class _StubRiskAgent:
    def __init__(self, repo_root: Path) -> None:
        self._repo_root = repo_root

    async def build_risk_payload(self, *, architecture_envelope) -> JSONObject:  # type: ignore[no-untyped-def]
        path = self._repo_root / "QUORUM_HAPPY.txt"
        with open(path, "a", encoding="utf-8") as f:
            f.write("risk\n")
        return {
            "target_repositories": ["DEMO_REPO"],
            "compliance_status": "pass",
            "risk_summary": ["low"],
            "recommended_actions": ["none"],
            "trace": {"architecture_signature": architecture_envelope.signature},
        }


class _StubBuildAgent:
    def __init__(self, repo_root: Path) -> None:
        self._repo_root = repo_root

    async def execute_build(self, *, envelope) -> JSONObject:  # type: ignore[no-untyped-def]
        text = (self._repo_root / "QUORUM_HAPPY.txt").read_text(encoding="utf-8")
        return {"status": "ok", "content": text, "correlation_id": envelope.correlation_id}


class TestQuorumConsensus(unittest.IsolatedAsyncioTestCase):
    async def test_happy_path_quorum_consensus(self) -> None:
        business_case = "\n".join(
            [
                "Quorum happy path integration: all validators pass.",
                "- Validate ballot aggregation",
                "- Verify transaction commits staged writes",
                "- Ensure checkpointing succeeds per stage",
            ]
        )

        with TemporaryDirectory() as tmp:
            repo_root = Path(tmp) / "repo"
            repo_root.mkdir(parents=True, exist_ok=True)
            logs_dir = Path(tmp) / "logs"
            governance = GovernanceLogger(root=logs_dir)
            checkpoint = CheckpointManager(logs_dir=logs_dir, business_case=business_case)

            intake_agent = _StubIntakeAgent()
            architect_agent = _StubArchitectAgent(repo_root)
            risk_agent = _StubRiskAgent(repo_root)
            build_agent = _StubBuildAgent(repo_root)

            stage_returns: list[bool] = []
            ballot_keys: list[list[str]] = []

            original_record_stage = checkpoint.record_stage

            def _wrapped_record_stage(*args, **kwargs):  # type: ignore[no-untyped-def]
                ok = original_record_stage(*args, **kwargs)
                stage_returns.append(bool(ok))
                ballots = kwargs.get("envelope_ballots")
                self.assertIsInstance(ballots, dict)
                ballot_keys.append(sorted(ballots.keys()))
                for ballot in ballots.values():
                    self.assertIsInstance(ballot, dict)
                    self.assertTrue(ballot.get("passed"))
                    sig = ballot.get("ballot_signature")
                    self.assertIsInstance(sig, str)
                    self.assertEqual(len(sig), 8)
                return ok

            with patch.object(checkpoint, "record_stage", new=_wrapped_record_stage):
                result = await run_three_stage_pipeline(
                    governance=governance,
                    intake_agent=intake_agent,
                    architect_agent=architect_agent,
                    risk_agent=risk_agent,
                    build_agent=build_agent,
                    business_case=business_case,
                    workspace_snapshot={"repo_root": str(repo_root)},
                    checkpoint=checkpoint,
                    resume=None,
                )

            self.assertEqual(result.get("status"), "ok")
            self.assertEqual((repo_root / "QUORUM_HAPPY.txt").read_text(encoding="utf-8"), "architect\nrisk\n")
            self.assertTrue(all(stage_returns), "Expected record_stage() to return True for all stages")
            self.assertEqual(len(ballot_keys), 3)
            for keys in ballot_keys:
                self.assertGreaterEqual(len(keys), 3)

            staging_dir = repo_root / ".workspace_staging" / checkpoint.token
            self.assertFalse(staging_dir.exists(), "Expected workspace staging to be fully cleaned after commits")
            self.assertFalse(
                checkpoint.checkpoint_path.exists(), "Expected checkpoint to be cleared after successful build"
            )

    async def test_quorum_dissent_vector_aborts_transaction_and_locks_state(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        test_path = repo_root / "QUORUM_DISSENT_TEST.txt"
        prior_text = test_path.read_text(encoding="utf-8") if test_path.exists() else None
        test_path.write_text("original\n", encoding="utf-8")

        business_case = "\n".join(
            [
                "Quorum dissent vector: force security worker rejection.",
                "- Inject VULNERABILITY footprint into Architecture -> Risk payload",
                "- Assert no partial writes escape staging",
                "- Assert governance transitions to QUORUM_LOCKED_INTERVENTION",
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

            original_impl = SoftwareArchitect.build_architecture_payload

            async def _patched(self: SoftwareArchitect, *, intake_envelope):  # type: ignore[no-untyped-def]
                with open(self.workspace.repo_root / "QUORUM_DISSENT_TEST.txt", "w", encoding="utf-8") as f:
                    f.write("should-not-commit\n")
                    f.flush()
                payload = await original_impl(self, intake_envelope=intake_envelope)
                plan = payload.get("architecture_plan")
                if isinstance(plan, list) and plan:
                    plan[0] = f"{plan[0]} VULNERABILITY"
                return payload

            with patch.object(SoftwareArchitect, "build_architecture_payload", new=_patched):
                rc = await asyncio.to_thread(run_autonomous_office.main, argv)

            self.assertEqual(rc, 2)
            self.assertEqual(test_path.read_text(encoding="utf-8"), "original\n")

            dissent_snapshot = log_dir / "QUORUM_DISSENT_SNAPSHOT.json"
            self.assertTrue(dissent_snapshot.exists(), "Expected QUORUM_DISSENT_SNAPSHOT.json to be written")
            snap = json.loads(dissent_snapshot.read_text(encoding="utf-8"))
            self.assertEqual(snap.get("event"), "QUORUM_DISSENT")
            dissenting = snap.get("dissenting_ballots", {})
            self.assertIn("security_validation_worker", dissenting)

            checkpoint_path = log_dir / "checkpoint_state.json"
            self.assertTrue(checkpoint_path.exists(), "Expected checkpoint_state.json to be created for intervention")
            chk = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            self.assertEqual(chk.get("governance_state"), "QUORUM_LOCKED_INTERVENTION")
            ballots = chk.get("envelope_ballots")
            self.assertIsInstance(ballots, dict)
            self.assertIn("security_validation_worker", ballots)

            token = chk.get("execution_token")
            self.assertIsInstance(token, str)
            staging_token_dir = repo_root / ".workspace_staging" / token
            self.assertFalse(
                staging_token_dir.exists(), "Expected dissent to rollback and clean workspace staging directory"
            )

            gov_path = log_dir / "governance.jsonl"
            self.assertTrue(gov_path.exists(), "Expected governance.jsonl to be created")
            lines = gov_path.read_text(encoding="utf-8", errors="replace").splitlines()
            self.assertTrue(any('"state":"QUORUM_LOCKED_INTERVENTION"' in ln for ln in lines))

        if prior_text is None:
            try:
                test_path.unlink(missing_ok=True)
            except OSError:
                pass
        else:
            test_path.write_text(prior_text, encoding="utf-8")


if __name__ == "__main__":
    unittest.main(verbosity=2)

