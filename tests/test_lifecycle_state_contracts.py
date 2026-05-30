from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from lifecycle_manager.lifecycle_contracts import AgentLifecycleState, validate_lifecycle_state_dict  # noqa: E402


class TestLifecycleStateContracts(unittest.TestCase):
    def _base(self) -> dict:
        return AgentLifecycleState(
            agent_id="a1",
            agent_class="C1",
            version="v1",
            status="registered",
            health="unknown",
            availability="available",
            assigned_repositories=[],
            current_missions=[],
            performance_summary={},
            lifecycle_notes=[],
            created_utc="2026-05-29T00:00:00Z",
            updated_utc="2026-05-29T00:00:00Z",
            metadata={},
        ).to_dict()

    def test_valid_state_passes(self) -> None:
        validate_lifecycle_state_dict(self._base())

    def test_invalid_status_fails(self) -> None:
        s = self._base()
        s["status"] = "bad"
        with self.assertRaises(ValueError):
            validate_lifecycle_state_dict(s)

    def test_invalid_health_fails(self) -> None:
        s = self._base()
        s["health"] = "bad"
        with self.assertRaises(ValueError):
            validate_lifecycle_state_dict(s)

    def test_invalid_availability_fails(self) -> None:
        s = self._base()
        s["availability"] = "bad"
        with self.assertRaises(ValueError):
            validate_lifecycle_state_dict(s)


if __name__ == "__main__":
    unittest.main()

