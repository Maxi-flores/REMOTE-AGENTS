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

from mission_engine.contracts import (  # noqa: E402
    ConsensusRecord,
    create_consensus_record,
    validate_consensus_record_dict,
)


class TestConsensusContracts(unittest.TestCase):
    def test_valid_consensus_record_passes_validation(self) -> None:
        record = create_consensus_record(
            mission_id="mission_1",
            task_id="task_1",
            consensus_type="twin",
            decision="approved",
            actor="ViteReactTwinAgent",
            agent_class="ViteReactTwinAgent",
            tool_name="workspace_file_router",
            target_repository="ConceptSHOP",
            feedback="Looks safe.",
            metadata={"review": "unit-test"},
        )
        validate_consensus_record_dict(record.to_dict())
        restored = ConsensusRecord.from_dict(record.to_dict())
        self.assertEqual(restored.consensus_type, "twin")
        self.assertEqual(restored.decision, "approved")

    def test_invalid_consensus_type_fails_validation(self) -> None:
        record = create_consensus_record(
            mission_id="mission_1",
            consensus_type="twin",
            decision="approved",
            actor="agent",
        ).to_dict()
        record["consensus_type"] = "committee-ish"
        with self.assertRaises(ValueError):
            validate_consensus_record_dict(record)

    def test_invalid_consensus_decision_fails_validation(self) -> None:
        record = create_consensus_record(
            mission_id="mission_1",
            consensus_type="human",
            decision="approved",
            actor="max",
        ).to_dict()
        record["decision"] = "shrugged"
        with self.assertRaises(ValueError):
            validate_consensus_record_dict(record)


if __name__ == "__main__":
    unittest.main()
