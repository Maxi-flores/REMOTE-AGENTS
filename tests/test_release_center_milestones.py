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

from release_center.milestones import build_release_milestones, summarize_release_milestones  # noqa: E402


class TestReleaseCenterMilestones(unittest.TestCase):
    def test_milestones_created_from_events(self) -> None:
        events = [
            {
                "event_id": "e1",
                "event_type": "readiness_report",
                "description": "Readiness status=ready, score=95",
                "status": "ready",
                "blockers": [],
                "warnings": [],
            },
            {
                "event_id": "e2",
                "event_type": "promotion_recommendation",
                "description": "Recommendation=promote",
                "status": "ready",
                "related_environment": "dev",
                "blockers": [],
                "warnings": [],
            },
        ]
        milestones = build_release_milestones(events)
        self.assertGreaterEqual(len(milestones), 2)

    def test_production_blockers_generate_escalation_hints(self) -> None:
        events = [
            {
                "event_id": "e1",
                "event_type": "promotion_recommendation",
                "description": "Recommendation=blocked",
                "status": "blocked",
                "related_environment": "production",
                "blockers": ["prod blocked"],
                "warnings": [],
            }
        ]
        milestones = build_release_milestones(events)
        summary = summarize_release_milestones(milestones)
        hints = summary["escalation_hints"]
        self.assertTrue(any("Production promotion is blocked" in h for h in hints))

    def test_rollback_ci_missing_generate_hints(self) -> None:
        events = [
            {
                "event_id": "e1",
                "event_type": "rollback_precheck",
                "description": "Rollback status=required",
                "status": "review_required",
                "related_environment": "staging",
                "blockers": [],
                "warnings": ["missing artifact"],
            },
            {
                "event_id": "e2",
                "event_type": "ci_handoff",
                "description": "Pipeline stage=ci-production",
                "status": "review_required",
                "related_environment": "production",
                "blockers": [],
                "warnings": [],
            },
        ]
        milestones = build_release_milestones(events)
        summary = summarize_release_milestones(milestones)
        hints = summary["escalation_hints"]
        self.assertTrue(any("Rollback requirements" in h for h in hints))
        self.assertTrue(any("CI handoff requirements" in h for h in hints))


if __name__ == "__main__":
    unittest.main()

