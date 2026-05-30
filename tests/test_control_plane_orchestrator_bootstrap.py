from __future__ import annotations

import json
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

from control_plane.bootstrap import bootstrap_advisory_artifacts  # noqa: E402
from control_plane.contracts import validate_control_plane_snapshot_dict  # noqa: E402
from release_center.timeline_contracts import validate_release_timeline_report_dict  # noqa: E402
from release_gates.contracts import validate_gate_decision_dict  # noqa: E402
from release_readiness.contracts import validate_release_readiness_report_dict  # noqa: E402
from sentient_ui.contracts import validate_view_model_envelope_dict  # noqa: E402


class TestControlPlaneOrchestratorBootstrap(unittest.TestCase):
    def test_bootstrap_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            result = bootstrap_advisory_artifacts(base)
            self.assertTrue(result["advisory_only"])
            self.assertTrue((base / ".missions").exists())
            self.assertTrue((base / ".scheduler" / "state.json").exists())
            self.assertTrue((base / ".governance" / "repositories.json").exists())
            self.assertTrue((base / ".memory" / "graph.json").exists())
            self.assertTrue((base / ".release_reports" / "release_readiness.json").exists())
            self.assertTrue((base / ".release_reports" / "gate_trace.json").exists())
            self.assertTrue((base / ".release_reports" / "release_timeline.json").exists())
            self.assertTrue((base / ".lifecycle" / "agents.json").exists())
            self.assertTrue((base / ".control_plane" / "snapshot.json").exists())
            self.assertTrue((base / ".sentient_ui" / "view_model.json").exists())

    def test_bootstrap_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            first = bootstrap_advisory_artifacts(base)
            second = bootstrap_advisory_artifacts(base)
            self.assertEqual(first["advisory_only"], second["advisory_only"])
            self.assertEqual(
                json.loads((base / ".scheduler" / "state.json").read_text(encoding="utf-8"))["schema_version"],
                1,
            )
            self.assertEqual(
                json.loads((base / ".memory" / "graph.json").read_text(encoding="utf-8"))["schema_version"],
                1,
            )

    def test_bootstrap_contract_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            bootstrap_advisory_artifacts(base)

            snapshot = json.loads((base / ".control_plane" / "snapshot.json").read_text(encoding="utf-8"))
            validate_control_plane_snapshot_dict(snapshot)

            view_model = json.loads((base / ".sentient_ui" / "view_model.json").read_text(encoding="utf-8"))
            validate_view_model_envelope_dict(view_model)

            readiness = json.loads((base / ".release_reports" / "release_readiness.json").read_text(encoding="utf-8"))
            validate_release_readiness_report_dict(readiness)

            gate_trace = json.loads((base / ".release_reports" / "gate_trace.json").read_text(encoding="utf-8"))
            validate_gate_decision_dict(gate_trace["decision"])

            timeline = json.loads((base / ".release_reports" / "release_timeline.json").read_text(encoding="utf-8"))
            validate_release_timeline_report_dict(timeline)


if __name__ == "__main__":
    unittest.main()

