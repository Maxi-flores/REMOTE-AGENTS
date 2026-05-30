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

from control_plane.contracts import (  # noqa: E402
    ControlPlaneSnapshot,
    DashboardSection,
    validate_control_plane_snapshot_dict,
    validate_dashboard_section_dict,
)


class TestControlPlaneContracts(unittest.TestCase):
    def test_valid_control_plane_snapshot_passes_validation(self) -> None:
        snapshot = ControlPlaneSnapshot(
            snapshot_id="snap_1",
            generated_utc="2026-01-01T00:00:00Z",
            schema_version=1,
            runtime={},
            missions={},
            agents={},
            repositories={},
            tools={},
            scheduler={},
            memory_graph={},
            approvals={},
            consensus={},
            queue={},
            observability={},
            metadata={},
        ).to_dict()
        validate_control_plane_snapshot_dict(snapshot)

    def test_invalid_snapshot_fails_validation(self) -> None:
        snapshot = {
            "snapshot_id": "snap_1",
            "generated_utc": "2026-01-01T00:00:00Z",
            "schema_version": 1,
            "runtime": [],
        }
        with self.assertRaises(ValueError):
            validate_control_plane_snapshot_dict(snapshot)  # type: ignore[arg-type]

    def test_valid_dashboard_section_passes_validation(self) -> None:
        section = DashboardSection(
            section_id="runtime",
            title="Runtime",
            status="healthy",
            summary="ok",
            metrics={},
            records=[],
            warnings=[],
            errors=[],
            metadata={},
        ).to_dict()
        validate_dashboard_section_dict(section)

    def test_invalid_section_status_fails_validation(self) -> None:
        section = DashboardSection(
            section_id="runtime",
            title="Runtime",
            status="healthy",
            summary="ok",
        ).to_dict()
        section["status"] = "great"
        with self.assertRaises(ValueError):
            validate_dashboard_section_dict(section)


if __name__ == "__main__":
    unittest.main()

