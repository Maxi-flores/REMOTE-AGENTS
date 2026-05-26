"""Async starvation mitigation rig for core.sandbox.

This rig validates that a malicious, CPU-bound blocking task cannot freeze the
main asyncio loop when executed through AgentSandboxExecutor in process mode.
"""

from __future__ import annotations

import asyncio
import time
import unittest
from pathlib import Path

from core.exceptions import PipelineHaltException
from core.sandbox import AgentSandboxExecutor


def _malicious_spin_forever() -> None:
    while True:
        pass


def _snapshot_workspace_staging(repo_root: Path) -> tuple[str, ...]:
    staging = repo_root / ".workspace_staging"
    if not staging.exists():
        return ()
    paths: list[str] = []
    for p in staging.rglob("*"):
        try:
            rel = p.relative_to(repo_root).as_posix()
        except Exception:
            rel = str(p)
        paths.append(rel)
    return tuple(sorted(paths))


class TestSandboxStarvationRig(unittest.IsolatedAsyncioTestCase):
    async def test_process_sandbox_prevents_event_loop_starvation(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        staging_before = _snapshot_workspace_staging(repo_root)

        ping_interval_s = 0.005
        ping_tasks = 20
        run_for_s = 0.25

        max_lag_s = 0.0
        lag_lock = asyncio.Lock()

        async def _pinger() -> None:
            nonlocal max_lag_s
            start = time.perf_counter()
            last = start
            while True:
                if time.perf_counter() - start >= run_for_s:
                    return
                await asyncio.sleep(ping_interval_s)
                now = time.perf_counter()
                lag = max(0.0, (now - last) - ping_interval_s)
                async with lag_lock:
                    if lag > max_lag_s:
                        max_lag_s = lag
                last = now

        async with AgentSandboxExecutor() as sandbox:
            pingers = [asyncio.create_task(_pinger(), name=f"ping-{idx}") for idx in range(ping_tasks)]
            try:
                with self.assertRaises(PipelineHaltException):
                    await sandbox.run(
                        "SoftwareArchitect.malicious_spin",
                        _malicious_spin_forever,
                        timeout_s=0.15,
                        mode="process",
                    )
            finally:
                await asyncio.gather(*pingers, return_exceptions=True)

        staging_after = _snapshot_workspace_staging(repo_root)
        self.assertEqual(staging_before, staging_after, "Expected .workspace_staging/ to remain unchanged")

        # Strict micro-latency threshold: allow modest scheduler noise, but no
        # freeze/jitter spikes that indicate loop starvation.
        self.assertLess(
            max_lag_s,
            0.03,
            f"Event loop lag exceeded threshold: max_lag_s={max_lag_s:.6f}s",
        )
