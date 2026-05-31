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

from portfolio_drift.checker import run_drift_checks  # noqa: E402


class TestPortfolioDriftChecker(unittest.TestCase):
    def test_detects_registry_dependency_mismatch(self) -> None:
        findings = run_drift_checks(
            registry={"repositories": [{"repository_id": "A", "enabled": True}]},
            dependency_registry={"dependencies": [{"repository_id": "B", "depends_on": ["A"]}]},
            bootstrap_report={"onboarding_records": [{"repository_id": "A", "artifact_status": "none"}], "generated_utc": "2026-01-01T00:00:00Z"},
            onboarding_report={"recommendations": [], "generated_utc": "2026-01-01T00:00:00Z"},
            dependency_report={"findings": [{"repository_id": "A", "severity": "high"}], "generated_utc": "2026-01-01T00:10:00Z"},
            critical_path_report={"recommendations": [], "generated_utc": "2026-01-01T00:00:00Z"},
            roadmap_report={"roadmap_items": [], "generated_utc": "2026-01-01T00:00:00Z"},
            progress_report={"metrics": [], "generated_utc": "2026-01-01T00:00:00Z"},
            portfolio_report={"repository_statuses": []},
        )
        drift_types = [f["drift_type"] for f in findings if isinstance(f, dict)]
        self.assertIn("missing_registry_reference", drift_types)
        self.assertIn("stale_recommendation", drift_types)
        self.assertIn("orphaned_critical_path_recommendation", drift_types)


if __name__ == "__main__":
    unittest.main()

