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

from execution_dossier.generator import generate_execution_dossier_report  # noqa: E402


class TestExecutionDossierGenerator(unittest.TestCase):
    def test_generates_dossiers_and_packets(self) -> None:
        report = generate_execution_dossier_report(
            work_queue_report={
                "report_id": "w1",
                "queue_items": [
                    {
                        "queue_item_id": "q1",
                        "source_refined_package_id": "r1",
                        "title": "mission_engine add_cli_test refinement",
                        "subsystem": "mission_engine",
                        "readiness_score": 95,
                        "risk_score": 20,
                        "execution_readiness": "ready",
                        "metadata": {"source_batch_id": "b1"},
                    }
                ],
            },
            base_dir=".",
        )
        self.assertEqual(len(report["dossiers"]), 1)
        self.assertEqual(len(report["execution_packets"]), 1)


if __name__ == "__main__":
    unittest.main()
