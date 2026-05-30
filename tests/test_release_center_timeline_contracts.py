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

from release_center.timeline_contracts import (  # noqa: E402
    ReleaseMilestone,
    ReleaseTimelineEvent,
    ReleaseTimelineReport,
    validate_release_milestone_dict,
    validate_release_timeline_event_dict,
    validate_release_timeline_report_dict,
)


class TestReleaseCenterTimelineContracts(unittest.TestCase):
    def test_valid_timeline_event_passes(self) -> None:
        payload = ReleaseTimelineEvent(
            event_id="e1",
            event_type="readiness_report",
            title="Readiness",
            description="desc",
            occurred_utc="2026-05-29T00:00:00Z",
            source_artifact=".release_reports/release_readiness.json",
            severity="info",
            status="observed",
            blockers=[],
            warnings=[],
            metadata={},
        ).to_dict()
        validate_release_timeline_event_dict(payload)

    def test_invalid_event_type_fails(self) -> None:
        with self.assertRaises(ValueError):
            validate_release_timeline_event_dict(
                {
                    "event_id": "e1",
                    "event_type": "bad",
                    "title": "x",
                    "description": "x",
                    "occurred_utc": "2026-05-29T00:00:00Z",
                    "source_artifact": ".",
                    "severity": "info",
                    "status": "observed",
                    "blockers": [],
                    "warnings": [],
                    "metadata": {},
                }
            )

    def test_valid_milestone_passes(self) -> None:
        payload = ReleaseMilestone(
            milestone_id="m1",
            title="M",
            description="D",
            milestone_type="readiness",
            status="ready",
            owner_placeholder="Release Owner",
            related_event_ids=["e1"],
            blockers=[],
            warnings=[],
            escalation_hints=[],
            metadata={},
        ).to_dict()
        validate_release_milestone_dict(payload)

    def test_invalid_milestone_status_fails(self) -> None:
        with self.assertRaises(ValueError):
            validate_release_milestone_dict(
                {
                    "milestone_id": "m1",
                    "title": "M",
                    "description": "D",
                    "milestone_type": "readiness",
                    "status": "done-ish",
                    "owner_placeholder": "Release Owner",
                    "related_event_ids": [],
                    "blockers": [],
                    "warnings": [],
                    "escalation_hints": [],
                    "metadata": {},
                }
            )

    def test_valid_timeline_report_passes(self) -> None:
        payload = ReleaseTimelineReport(
            report_id="r1",
            generated_utc="2026-05-29T00:00:00Z",
            release_label="local-release",
            timeline_events=[],
            milestones=[],
            summary={},
            escalation_hints=[],
            advisory_only=True,
            metadata={},
        ).to_dict()
        validate_release_timeline_report_dict(payload)


if __name__ == "__main__":
    unittest.main()

