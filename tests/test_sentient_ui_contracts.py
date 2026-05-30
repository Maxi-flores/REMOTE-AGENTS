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

from sentient_ui.contracts import (  # noqa: E402
    PanelViewModel,
    ViewModelEnvelope,
    validate_panel_view_model_dict,
    validate_view_model_envelope_dict,
)


class TestSentientUiContracts(unittest.TestCase):
    def test_valid_view_model_envelope_passes_validation(self) -> None:
        panel = PanelViewModel(panel_id="runtime_panel", title="Runtime", status="healthy", summary="ok").to_dict()
        envelope = ViewModelEnvelope(
            view_model_id="vm_1",
            generated_utc="2026-01-01T00:00:00Z",
            source_snapshot_id="snap_1",
            schema_version=1,
            runtime_panel=panel,
            mission_panel=panel,
            agent_panel=panel,
            repository_panel=panel,
            tool_panel=panel,
            scheduler_panel=panel,
            memory_panel=panel,
            approval_panel=panel,
            consensus_panel=panel,
            observability_panel=panel,
            alerts=[],
            metadata={},
        ).to_dict()
        validate_view_model_envelope_dict(envelope)

    def test_invalid_envelope_fails_validation(self) -> None:
        bad = {"view_model_id": "x", "generated_utc": "t", "source_snapshot_id": "s", "schema_version": 1}
        with self.assertRaises(ValueError):
            validate_view_model_envelope_dict(bad)  # type: ignore[arg-type]

    def test_valid_panel_view_model_passes_validation(self) -> None:
        panel = PanelViewModel(panel_id="runtime_panel", title="Runtime", status="healthy", summary="ok").to_dict()
        validate_panel_view_model_dict(panel)

    def test_invalid_panel_status_fails_validation(self) -> None:
        panel = PanelViewModel(panel_id="runtime_panel", title="Runtime", status="healthy", summary="ok").to_dict()
        panel["status"] = "amazing"
        with self.assertRaises(ValueError):
            validate_panel_view_model_dict(panel)


if __name__ == "__main__":
    unittest.main()

