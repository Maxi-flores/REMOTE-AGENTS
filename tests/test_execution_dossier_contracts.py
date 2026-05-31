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

from execution_dossier.contracts import (  # noqa: E402
    validate_execution_dossier_dict,
    validate_execution_dossier_report_dict,
    validate_execution_packet_dict,
)


class TestExecutionDossierContracts(unittest.TestCase):
    def test_contract_validation(self) -> None:
        dossier = {
            "dossier_id": "d1",
            "generated_utc": "2026-01-01T00:00:00Z",
            "source_queue_item_id": "q1",
            "source_package_id": "p1",
            "title": "t",
            "objective": "o",
            "subsystem": "mission_engine",
            "target_files": ["tests/test_mission_engine_cli.py"],
            "expected_changes": {},
            "validation_commands": ["python -m unittest -v"],
            "rollback_guidance": ["revert file"],
            "review_checklist": ["Target files reviewed"],
            "execution_readiness_score": 90,
            "execution_risk": "low",
            "advisory_only": True,
            "metadata": {},
        }
        packet = {
            "packet_id": "p1",
            "dossier_id": "d1",
            "codex_prompt": "x",
            "execution_summary": "y",
            "validation_summary": "z",
            "advisory_only": True,
            "metadata": {},
        }
        report = {
            "report_id": "r1",
            "generated_utc": "2026-01-01T00:00:00Z",
            "dossiers": [dossier],
            "execution_packets": [packet],
            "advisory_only": True,
            "metadata": {},
        }
        validate_execution_dossier_dict(dossier)
        validate_execution_packet_dict(packet)
        validate_execution_dossier_report_dict(report)


if __name__ == "__main__":
    unittest.main()
