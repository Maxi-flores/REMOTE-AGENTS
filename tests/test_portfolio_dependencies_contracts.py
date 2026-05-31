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

from portfolio_dependencies.contracts import (  # noqa: E402
    DependencyGraphReport,
    new_id,
    utc_now,
    validate_dependency_graph_report_dict,
)


class TestPortfolioDependenciesContracts(unittest.TestCase):
    def test_contract(self) -> None:
        payload = DependencyGraphReport(
            report_id=new_id("dep_report"),
            generated_utc=utc_now(),
            dependency_graph={"A": ["B"]},
            dependency_chains=[["A", "B"]],
            findings=[
                {
                    "finding_id": "f1",
                    "severity": "high",
                    "repository_id": "A",
                    "dependency_repository_id": "B",
                    "category": "dependency_blocked",
                    "title": "t",
                    "description": "d",
                    "impact": "i",
                    "recommended_action": "r",
                    "metadata": {},
                }
            ],
            portfolio_impact={},
            advisory_only=True,
            metadata={},
        ).to_dict()
        validate_dependency_graph_report_dict(payload)


if __name__ == "__main__":
    unittest.main()

