import asyncio
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import run_autonomous_office
from agents.software_architect import SoftwareArchitect
from core.proof_ledger import iter_ledger_blocks, verify_ledger_blocks
from core.replay import PipelineReplayController, ReadOnlyWorkspaceGuard


class TestForensicReplay(unittest.IsolatedAsyncioTestCase):
    async def test_forensic_ledger_replay_reconstructs_dissent_deterministically(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        live_path = repo_root / "FORENSIC_REPLAY_TEST.txt"
        prior_text = live_path.read_text(encoding="utf-8") if live_path.exists() else None
        live_path.write_text("baseline\n", encoding="utf-8")

        business_case = "\n".join(
            [
                "Forensic replay rig: force Byzantine quorum dissent and replay deterministically.",
                "- Inject a security marker into Architecture -> Risk payload",
                "- Ensure staged writes never escape into live repo during replay",
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
                # This write must be staged and rolled back, never committed.
                with open(self.workspace.repo_root / "FORENSIC_REPLAY_TEST.txt", "w", encoding="utf-8") as f:
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
            self.assertEqual(live_path.read_text(encoding="utf-8"), "baseline\n")

            ledger_path = log_dir / "PROOFS_LEDGER.jsonl"
            self.assertTrue(ledger_path.exists(), "Expected PROOFS_LEDGER.jsonl to be written")
            dissent_snapshot = log_dir / "QUORUM_DISSENT_SNAPSHOT.json"
            self.assertTrue(dissent_snapshot.exists(), "Expected QUORUM_DISSENT_SNAPSHOT.json to be written")

            ledger_text_before = ledger_path.read_text(encoding="utf-8", errors="replace")
            verified = verify_ledger_blocks(iter_ledger_blocks(ledger_path))

            staging_root = repo_root / ".workspace_staging"
            staging_before_exists = staging_root.exists()
            staging_before = []
            if staging_before_exists:
                staging_before = sorted(str(p.relative_to(repo_root)) for p in staging_root.rglob("*"))

            expected_frames: list[str] = []
            for block in verified:
                payload = block.get("payload")
                if not isinstance(payload, dict):
                    continue
                kind = payload.get("kind")
                if kind == "GOV_EVENT":
                    ev = payload.get("event")
                    if isinstance(ev, dict) and isinstance(ev.get("event"), str):
                        expected_frames.append(str(ev["event"]))
                        continue
                if isinstance(kind, str) and kind:
                    expected_frames.append(kind)
                    continue
                ev = payload.get("event")
                if isinstance(ev, str) and ev:
                    expected_frames.append(ev)
                    continue
                expected_frames.append("UNKNOWN")

            controller = PipelineReplayController(repo_root=repo_root, log_dir=log_dir)
            snapshots: list[Path] = []

            async def _on_step(frame):  # type: ignore[no-untyped-def]
                if frame.frame_kind == "TX_ROLLBACK" and frame.staging_snapshot is not None:
                    snapshots.append(frame.staging_snapshot)

            try:
                with ReadOnlyWorkspaceGuard(repo_root):
                    result = await controller.replay_step_loop(source=str(ledger_path), on_step=_on_step)

                self.assertEqual(result.frames, expected_frames)
                self.assertGreater(result.verified_blocks, 0)

                # Replay must not mutate the ledger (pure verification).
                ledger_text_after = ledger_path.read_text(encoding="utf-8", errors="replace")
                self.assertEqual(ledger_text_after, ledger_text_before)

                # Ensure the replay sandbox created at least one peekable staging snapshot for the dissent rollback.
                self.assertTrue(snapshots, "Expected at least one TX_ROLLBACK staging snapshot during replay")
                staged_file_found = False
                for snap_root in snapshots:
                    candidate = snap_root / "0" / "FORENSIC_REPLAY_TEST.txt"
                    if candidate.exists():
                        staged_file_found = True
                        self.assertEqual(candidate.read_text(encoding="utf-8"), "should-not-commit\n")
                self.assertTrue(staged_file_found, "Expected staged FORENSIC_REPLAY_TEST.txt inside replay snapshot")

                # Ensure no staging escaped into the live repository during replay.
                self.assertEqual(staging_root.exists(), staging_before_exists)
                if staging_before_exists:
                    staging_after = sorted(str(p.relative_to(repo_root)) for p in staging_root.rglob("*"))
                    self.assertEqual(staging_after, staging_before)
                self.assertEqual(live_path.read_text(encoding="utf-8"), "baseline\n")
            finally:
                controller.close()

        if prior_text is None:
            try:
                live_path.unlink(missing_ok=True)
            except OSError:
                pass
        else:
            live_path.write_text(prior_text, encoding="utf-8")


if __name__ == "__main__":
    unittest.main(verbosity=2)
