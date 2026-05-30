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

from control_plane.orchestrator_contracts import (  # noqa: E402
    validate_orchestration_report_dict,
    validate_orchestration_request_dict,
    validate_orchestration_stage_result_dict,
)


class TestControlPlaneOrchestratorContracts(unittest.TestCase):
    def test_valid_request(self) -> None:
        payload = {
            "orchestration_id": "cpo_1",
            "trigger_source": "manual",
            "task_ids": [],
            "target_repositories": [],
            "requested_utc": "2026-01-01T00:00:00Z",
            "advisory_only": True,
            "metadata": {},
        }
        validate_orchestration_request_dict(payload)

    def test_stage_requires_advisory_true(self) -> None:
        payload = {
            "stage_name": "mission",
            "status": "ok",
            "input_refs": [],
            "output_refs": [],
            "warnings": [],
            "blockers": [],
            "summary": {},
            "completed_utc": "2026-01-01T00:00:00Z",
            "advisory_only": False,
            "metadata": {},
        }
        with self.assertRaises(ValueError):
            validate_orchestration_stage_result_dict(payload)

    def test_valid_report(self) -> None:
        stage = {
            "stage_name": "mission",
            "status": "ok",
            "input_refs": [],
            "output_refs": [],
            "warnings": [],
            "blockers": [],
            "summary": {},
            "completed_utc": "2026-01-01T00:00:00Z",
            "advisory_only": True,
            "metadata": {},
        }
        payload = {
            "report_id": "cpo_report_1",
            "orchestration_id": "cpo_1",
            "generated_utc": "2026-01-01T00:00:00Z",
            "pipeline_status": "ok",
            "stage_results": [stage],
            "cross_stage_findings": [],
            "recommended_next_actions": [],
            "advisory_only": True,
            "metadata": {},
        }
        validate_orchestration_report_dict(payload)


if __name__ == "__main__":
    unittest.main()

