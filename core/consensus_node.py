"""Async TCP-based BFT state machine replication (stdlib-only, Python 3.10+).

This module introduces a lightweight PBFT-inspired 3-phase replication engine
for ordering proof-ledger blocks across multiple remote runner nodes before they
are committed to disk.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


@dataclass(slots=True)
class BFTConsensusNode:
    """Cluster peer participating in 3-phase block replication."""

    node_id: str
    repo_root: Path
    log_dir: Path
    topology_path: Path
    execution_token: str

    async def start(self) -> None:
        raise NotImplementedError

    async def stop(self) -> None:
        raise NotImplementedError

    async def submit_payload(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        """Submit a candidate transaction payload to be ordered and committed."""
        raise NotImplementedError

