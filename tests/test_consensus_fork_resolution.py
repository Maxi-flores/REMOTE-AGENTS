import asyncio
import hashlib
import json
import threading
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Mapping, MutableMapping
from unittest.mock import patch

from core.fork_resolver import CryptographicForkException, LedgerForkAuditor
from core.hashutil import fnv1a_32
from core.proof_ledger import ProofLedgerManager, iter_ledger_blocks, verify_ledger_blocks
from core.replay import PipelineReplayController, ReadOnlyWorkspaceGuard


def _canonical_json(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _compute_block_hash(block_without_hash_and_sig: Mapping[str, Any]) -> str:
    material = _canonical_json(block_without_hash_and_sig).encode("utf-8", errors="surrogatepass")
    return hashlib.sha256(material).hexdigest()


def _compute_block_signature(block_without_sig: Mapping[str, Any]) -> str:
    return fnv1a_32(_canonical_json(block_without_sig))


def _signed_block(*, index: int, execution_token: str, prev_hash: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    header: MutableMapping[str, Any] = {
        "index": index,
        "ts_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "execution_token": execution_token,
        "prev_hash": prev_hash,
        "payload": dict(payload),
    }
    h = _compute_block_hash(header)
    header["hash"] = h
    header["signature"] = _compute_block_signature(header)
    return dict(header)


class TestConsensusForkResolution(unittest.IsolatedAsyncioTestCase):
    async def test_fork_auditor_detects_and_resolves_duplicate_index_fork(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        sentinel = repo_root / "FORK_RESOLUTION_TEST.txt"
        prior_text = sentinel.read_text(encoding="utf-8") if sentinel.exists() else None
        sentinel.write_text("baseline\n", encoding="utf-8")

        with TemporaryDirectory() as tmp:
            log_dir = Path(tmp) / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            token = "a" * 64

            ledger = ProofLedgerManager(logs_dir=log_dir, execution_token=token)
            for i in range(14):
                ledger.append_block({"kind": "NOOP", "i": i})

            ledger_path = log_dir / "PROOFS_LEDGER.jsonl"
            self.assertTrue(ledger_path.exists())

            # Boot replay deterministically up to index 13 (ledger lines 0..13).
            lines = ledger_path.read_text(encoding="utf-8", errors="replace").splitlines(True)
            up_to_13 = log_dir / "UP_TO_13.jsonl"
            up_to_13.write_text("".join(lines[:14]), encoding="utf-8")

            controller = PipelineReplayController(repo_root=repo_root, log_dir=log_dir)
            try:
                with ReadOnlyWorkspaceGuard(repo_root):
                    result = await controller.replay_step_loop(source=str(up_to_13))
                self.assertEqual(result.verified_blocks, 14)
            finally:
                controller.close()

            blocks = list(iter_ledger_blocks(ledger_path))
            block_13 = next(b for b in blocks if int(b.get("index", -1)) == 13)
            prev = str(block_13["hash"])

            # Inject a concurrent fork: two different blocks share index 14 with the same prev_hash.
            fork_a = _signed_block(index=14, execution_token=token, prev_hash=prev, payload={"kind": "TX_COMMIT", "branch": "A"})
            fork_b = _signed_block(index=14, execution_token=token, prev_hash=prev, payload={"kind": "TX_COMMIT", "branch": "B"})
            a15 = _signed_block(index=15, execution_token=token, prev_hash=str(fork_a["hash"]), payload={"kind": "QUORUM_PASSED", "branch": "A"})

            with ledger_path.open("a", encoding="utf-8") as f:
                f.write(_canonical_json(fork_a) + "\n")
                f.write(_canonical_json(fork_b) + "\n")
                f.write(_canonical_json(a15) + "\n")

            auditor = LedgerForkAuditor(repo_root=repo_root, log_dir=log_dir)
            with self.assertRaises(CryptographicForkException):
                auditor.audit_or_raise()

            entered_guard = threading.Event()
            real_guard = ReadOnlyWorkspaceGuard

            class _RecordingGuard:
                def __init__(self, root: Path) -> None:
                    self._inner = real_guard(root)

                def __enter__(self):
                    entered_guard.set()
                    return self._inner.__enter__()

                def __exit__(self, exc_type, exc, tb):  # type: ignore[no-untyped-def]
                    return self._inner.__exit__(exc_type, exc, tb)

            with patch("core.fork_resolver.ReadOnlyWorkspaceGuard", new=_RecordingGuard):
                resolution = await auditor.resolve_fork_async()

            self.assertTrue(entered_guard.is_set(), "Expected fork resolver to use ReadOnlyWorkspaceGuard during replay evaluation")
            self.assertTrue(resolution.orphaned_path.exists())

            # Ledger must be linear again.
            auditor.audit_or_raise()

            verified = verify_ledger_blocks(iter_ledger_blocks(ledger_path))
            payload_14 = verified[14]["payload"]
            self.assertIsInstance(payload_14, dict)
            self.assertEqual(payload_14.get("branch"), "A")

            last_payload = verified[-1]["payload"]
            self.assertIsInstance(last_payload, dict)
            self.assertEqual(last_payload.get("kind"), "CONSENSUS_RECONCILIATION_COMPLETE")

            orphaned_text = resolution.orphaned_path.read_text(encoding="utf-8", errors="replace")
            self.assertIn('"branch":"B"', orphaned_text)

            # Fork resolution must not mutate workspace files.
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "baseline\n")

        if prior_text is None:
            try:
                sentinel.unlink(missing_ok=True)
            except OSError:
                pass
        else:
            sentinel.write_text(prior_text, encoding="utf-8")


if __name__ == "__main__":
    unittest.main(verbosity=2)

