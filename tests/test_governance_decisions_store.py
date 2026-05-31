from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from governance_decisions.store import append_decision, load_decisions  # noqa: E402


class TestGovernanceDecisionsStore(unittest.TestCase):
    def test_append_and_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".control_plane" / "governance_decisions" / "decisions.json"
            state = append_decision(
                {
                    "decision_id": "d1",
                    "packet_id": "p1",
                    "source_dossier_id": "s1",
                    "decision": "defer",
                    "reviewer": "Max",
                    "decision_notes": "defer",
                    "decided_utc": "2026-01-01T00:00:00Z",
                    "safety_acknowledgements": [],
                    "advisory_only": True,
                    "metadata": {},
                },
                path=path,
            )
            self.assertEqual(len(state["decisions"]), 1)
            loaded = load_decisions(path)
            self.assertEqual(len(loaded["decisions"]), 1)

    def test_idempotent_replace_by_decision_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".control_plane" / "governance_decisions" / "decisions.json"
            payload = {
                "decision_id": "d1",
                "packet_id": "p1",
                "source_dossier_id": "s1",
                "decision": "defer",
                "reviewer": "Max",
                "decision_notes": "defer",
                "decided_utc": "2026-01-01T00:00:00Z",
                "safety_acknowledgements": [],
                "advisory_only": True,
                "metadata": {},
            }
            append_decision(payload, path=path)
            payload2 = dict(payload)
            payload2["decision_notes"] = "updated"
            append_decision(payload2, path=path)
            loaded = load_decisions(path)
            self.assertEqual(len(loaded["decisions"]), 1)
            self.assertEqual(loaded["decisions"][0]["decision_notes"], "updated")


if __name__ == "__main__":
    unittest.main()

