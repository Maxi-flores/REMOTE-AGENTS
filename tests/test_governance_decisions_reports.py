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

from governance_decisions.reports import generate_governance_decision_summary_report  # noqa: E402


class TestGovernanceDecisionsReports(unittest.TestCase):
    def test_pending_detection(self) -> None:
        report = generate_governance_decision_summary_report(
            packet_report={"report_id": "p1", "packets": [{"packet_id": "a"}, {"packet_id": "b"}]},
            decisions_state={"schema_version": 1, "decisions": [{"decision_id": "d1", "packet_id": "a", "source_dossier_id": "x", "decision": "defer", "reviewer": "Max", "decision_notes": "n", "decided_utc": "2026-01-01T00:00:00Z", "safety_acknowledgements": [], "advisory_only": True, "metadata": {}}]},
        )
        self.assertEqual(report["summary"]["pending"], 1)
        self.assertEqual(report["summary"]["deferred"], 1)

    def test_report_paths_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = generate_governance_decision_summary_report(base_dir=Path(tmp))
            self.assertTrue(report["advisory_only"])


if __name__ == "__main__":
    unittest.main()

