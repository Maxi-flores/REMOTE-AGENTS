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

from strategic_missions.contracts import (  # noqa: E402
    validate_strategic_mission_candidate_dict,
    validate_strategic_mission_report_dict,
)


class TestStrategicMissionsContracts(unittest.TestCase):
    def test_candidate_contract_valid(self) -> None:
        payload = {
            "candidate_id": "c1",
            "title": "Improve lifecycle coverage",
            "description": "desc",
            "source_finding_ids": ["f1"],
            "category": "lifecycle",
            "priority": "P1",
            "risk_reduction_score": 80,
            "effort_score": 40,
            "confidence_score": 85,
            "recommended_repository": None,
            "suggested_instruction": "Do thing",
            "advisory_only": True,
            "metadata": {},
        }
        validate_strategic_mission_candidate_dict(payload)

    def test_report_contract_valid(self) -> None:
        payload = {
            "report_id": "r1",
            "generated_utc": "2026-01-01T00:00:00Z",
            "overall_status": "warning",
            "candidates": [],
            "recommended_sequence": [],
            "summary": {},
            "advisory_only": True,
            "metadata": {},
        }
        validate_strategic_mission_report_dict(payload)


if __name__ == "__main__":
    unittest.main()

