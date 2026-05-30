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

from executive_briefing.contracts import validate_executive_briefing_dict, validate_executive_finding_dict  # noqa: E402


class TestExecutiveBriefingContracts(unittest.TestCase):
    def test_valid_finding(self) -> None:
        validate_executive_finding_dict(
            {
                "finding_id": "f1",
                "severity": "high",
                "category": "release",
                "title": "t",
                "description": "d",
                "recommended_action": "a",
            }
        )

    def test_valid_briefing(self) -> None:
        payload = {
            "briefing_id": "b1",
            "generated_utc": "2026-01-01T00:00:00Z",
            "overall_status": "healthy",
            "executive_summary": "ok",
            "top_risks": [],
            "blocked_items": [],
            "recommended_actions": [],
            "release_summary": {},
            "lifecycle_summary": {},
            "governance_summary": {},
            "metadata": {},
        }
        validate_executive_briefing_dict(payload)


if __name__ == "__main__":
    unittest.main()

