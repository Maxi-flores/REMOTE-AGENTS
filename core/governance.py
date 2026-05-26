"""Governance logging and pipeline state reporting."""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from core.types import JSONObject

GovernanceState = Literal["Running", "Pending Intervention", "QUORUM_LOCKED_INTERVENTION", "Completed"]


@dataclass(slots=True)
class GovernanceLogger:
    root: Path
    stream: Any = sys.stdout
    state: GovernanceState = "Running"

    def __post_init__(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    @property
    def log_path(self) -> Path:
        return self.root / "governance.jsonl"

    def set_state(self, state: GovernanceState) -> None:
        self.state = state
        self.emit_event(
            {
                "event": "STATE",
                "state": state,
            }
        )

    def emit_event(self, event: JSONObject) -> None:
        enriched = dict(event)
        enriched["ts"] = time.time()
        enriched["governance_state"] = self.state
        line = json.dumps(enriched, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        try:
            self.stream.write(line + "\n")
            self.stream.flush()
        except Exception:
            pass
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass
