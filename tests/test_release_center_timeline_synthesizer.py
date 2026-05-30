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

from release_center.timeline_synthesizer import (  # noqa: E402
    event_from_readiness_report,
    events_from_gate_trace,
    events_from_promotion_report,
    events_from_scenario_comparison,
    sort_timeline_events,
)


class TestReleaseCenterTimelineSynthesizer(unittest.TestCase):
    def test_readiness_report_creates_event(self) -> None:
        event = event_from_readiness_report({"readiness_status": "ready", "readiness_score": 95})
        self.assertEqual(event["event_type"], "readiness_report")

    def test_gate_trace_creates_gate_event(self) -> None:
        events = events_from_gate_trace({"decision": {"decision": "pass"}})
        self.assertEqual(events[0]["event_type"], "gate_decision")

    def test_scenario_comparison_creates_scenario_event(self) -> None:
        events = events_from_scenario_comparison({"comparison": {"aggregate_decision": "pass", "aggregate_status": "ready"}})
        self.assertEqual(events[0]["event_type"], "scenario_comparison")

    def test_promotion_report_creates_env_specific_events(self) -> None:
        events = events_from_promotion_report(
            {
                "recommendations": [
                    {
                        "recommendation_id": "r1",
                        "recommendation": "promote",
                        "target_environment": "dev",
                        "rollback_precheck": {"rollback_plan_status": "ready"},
                        "ci_handoff": {"recommended_checks": ["x"], "suggested_pipeline_stage": "ci-dev"},
                    }
                ]
            }
        )
        types = [e["event_type"] for e in events]
        self.assertIn("promotion_recommendation", types)
        self.assertIn("rollback_precheck", types)
        self.assertIn("ci_handoff", types)

    def test_timeline_sorting_is_chronological(self) -> None:
        events = [
            {"event_id": "1", "occurred_utc": "2026-05-29T00:00:02Z"},
            {"event_id": "2", "occurred_utc": "2026-05-29T00:00:01Z"},
        ]
        sorted_events = sort_timeline_events(events)
        self.assertEqual(sorted_events[0]["event_id"], "2")


if __name__ == "__main__":
    unittest.main()

