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

from release_readiness.contracts import (  # noqa: E402
    ContractDriftFinding,
    ReleaseReadinessReport,
    validate_contract_drift_finding_dict,
    validate_release_readiness_report_dict,
)


class TestReleaseReadinessContracts(unittest.TestCase):
    def test_valid_contract_drift_finding_passes_validation(self) -> None:
        payload = ContractDriftFinding(
            finding_id="f1",
            artifact_type="control_plane_snapshot",
            artifact_path=".control_plane/snapshot.json",
            drift_type="missing_required_field",
            severity="error",
            field_path="runtime",
            expected="present",
            actual="missing",
            message="Required field missing",
        ).to_dict()
        validate_contract_drift_finding_dict(payload)

    def test_invalid_drift_type_fails_validation(self) -> None:
        payload = ContractDriftFinding(
            finding_id="f1",
            artifact_type="control_plane_snapshot",
            artifact_path="x",
            drift_type="missing_required_field",
            severity="error",
            field_path="x",
            expected="x",
            actual="x",
            message="x",
        ).to_dict()
        payload["drift_type"] = "banana"
        with self.assertRaises(ValueError):
            validate_contract_drift_finding_dict(payload)

    def test_invalid_severity_fails_validation(self) -> None:
        payload = ContractDriftFinding(
            finding_id="f1",
            artifact_type="control_plane_snapshot",
            artifact_path="x",
            drift_type="missing_required_field",
            severity="error",
            field_path="x",
            expected="x",
            actual="x",
            message="x",
        ).to_dict()
        payload["severity"] = "mild"
        with self.assertRaises(ValueError):
            validate_contract_drift_finding_dict(payload)

    def test_valid_release_readiness_report_passes_validation(self) -> None:
        payload = ReleaseReadinessReport(
            report_id="r1",
            generated_utc="2026-01-01T00:00:00Z",
            scope="sentient-control-plane",
            readiness_score=95,
            readiness_status="ready",
            blockers=[],
            warnings=[],
            findings=[],
            checked_artifacts=[],
            summary={},
        ).to_dict()
        validate_release_readiness_report_dict(payload)

    def test_invalid_readiness_status_fails_validation(self) -> None:
        payload = ReleaseReadinessReport(
            report_id="r1",
            generated_utc="2026-01-01T00:00:00Z",
            scope="sentient-control-plane",
            readiness_score=95,
            readiness_status="ready",
            blockers=[],
            warnings=[],
            findings=[],
            checked_artifacts=[],
            summary={},
        ).to_dict()
        payload["readiness_status"] = "great"
        with self.assertRaises(ValueError):
            validate_release_readiness_report_dict(payload)


if __name__ == "__main__":
    unittest.main()

