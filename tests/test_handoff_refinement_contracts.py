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

from handoff_refinement.contracts import (  # noqa: E402
    validate_refined_implementation_package_dict,
    validate_refinement_report_dict,
)


class TestHandoffRefinementContracts(unittest.TestCase):
    def test_contract_validation(self) -> None:
        pkg = {
            "refined_package_id": "rp1",
            "source_package_id": "p1",
            "source_batch_id": "b1",
            "title": "title",
            "objective": "obj",
            "subsystem": "mission_engine",
            "change_type": "add_cli_test",
            "target_files": ["tests/test_mission_engine_cli.py"],
            "expected_changes": {},
            "validation_commands": ["python -m unittest -v"],
            "risk_level": "low",
            "estimated_scope": "tiny",
            "traceability_refs": ["p1", "b1"],
            "codex_prompt": {"prompt_id": "pp1", "prompt_text": "x", "advisory_only": True, "metadata": {}},
            "advisory_only": True,
            "metadata": {},
        }
        report = {
            "report_id": "rr1",
            "generated_utc": "2026-01-01T00:00:00Z",
            "source_handoff_report_id": "h1",
            "refined_packages": [pkg],
            "split_summary": {},
            "advisory_only": True,
            "metadata": {},
        }
        validate_refined_implementation_package_dict(pkg)
        validate_refinement_report_dict(report)


if __name__ == "__main__":
    unittest.main()
