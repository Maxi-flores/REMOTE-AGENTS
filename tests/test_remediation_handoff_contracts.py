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

from remediation_handoff.contracts import (  # noqa: E402
    validate_codex_implementation_prompt_dict,
    validate_implementation_package_dict,
    validate_implementation_package_report_dict,
)


class TestRemediationHandoffContracts(unittest.TestCase):
    def test_valid_contracts(self) -> None:
        package = {
            "package_id": "p1",
            "generated_utc": "2026-01-01T00:00:00Z",
            "source_batch_id": "b1",
            "title": "Title",
            "objective": "Objective",
            "target_files": ["tests/test_x.py"],
            "expected_changes": {"file_additions": ["tests/test_x.py"], "file_updates": [], "notes": []},
            "validation_commands": ["python -m unittest -v"],
            "risks": ["Low"],
            "advisory_only": True,
            "metadata": {},
        }
        prompt = {
            "prompt_id": "pr1",
            "package_id": "p1",
            "prompt_text": "Do thing",
            "advisory_only": True,
            "metadata": {},
        }
        package["codex_prompt"] = prompt
        report = {
            "report_id": "r1",
            "generated_utc": "2026-01-01T00:00:00Z",
            "source_remediation_report_id": "rr1",
            "packages": [package],
            "advisory_only": True,
            "metadata": {},
        }
        validate_implementation_package_dict(package)
        validate_codex_implementation_prompt_dict(prompt)
        validate_implementation_package_report_dict(report)


if __name__ == "__main__":
    unittest.main()
