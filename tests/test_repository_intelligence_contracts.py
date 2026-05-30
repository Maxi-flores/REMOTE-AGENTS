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

from repository_intelligence.contracts import (  # noqa: E402
    validate_repository_coverage_finding_dict,
    validate_repository_intelligence_report_dict,
    validate_repository_inventory_dict,
)


class TestRepositoryIntelligenceContracts(unittest.TestCase):
    def test_inventory_contract(self) -> None:
        payload = {
            "inventory_id": "i1",
            "generated_utc": "2026-01-01T00:00:00Z",
            "root_path": "C:/repo",
            "source_directories": [],
            "test_files": [],
            "documentation_files": [],
            "config_files": [],
            "package_files": [],
            "runtime_entrypoints": [],
            "advisory_only": True,
            "metadata": {},
        }
        validate_repository_inventory_dict(payload)

    def test_finding_contract(self) -> None:
        payload = {
            "finding_id": "f1",
            "category": "testing",
            "severity": "medium",
            "title": "t",
            "description": "d",
            "path_refs": [],
            "recommended_action": "a",
            "advisory_only": True,
            "metadata": {},
        }
        validate_repository_coverage_finding_dict(payload)

    def test_report_contract(self) -> None:
        payload = {
            "report_id": "r1",
            "generated_utc": "2026-01-01T00:00:00Z",
            "repository_name": "REMOTE-AGENTS",
            "overall_status": "warning",
            "inventory": {
                "inventory_id": "i1",
                "generated_utc": "2026-01-01T00:00:00Z",
                "root_path": "C:/repo",
                "source_directories": [],
                "test_files": [],
                "documentation_files": [],
                "config_files": [],
                "package_files": [],
                "runtime_entrypoints": [],
                "advisory_only": True,
                "metadata": {},
            },
            "findings": [],
            "suggested_mission_opportunities": [],
            "advisory_only": True,
            "metadata": {},
        }
        validate_repository_intelligence_report_dict(payload)


if __name__ == "__main__":
    unittest.main()

