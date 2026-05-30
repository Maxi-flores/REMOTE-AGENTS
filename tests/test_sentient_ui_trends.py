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

from sentient_ui.trends import (  # noqa: E402
    build_metric_series,
    compute_delta,
    compute_status_trend,
    summarize_recent_alerts,
)


class TestSentientUiTrends(unittest.TestCase):
    def test_trend_helper_builds_metric_series(self) -> None:
        history = [
            {"snapshot_id": "s1", "generated_utc": "t1", "missions": {"metrics": {"total_missions": 1}}},
            {"snapshot_id": "s2", "generated_utc": "t2", "missions": {"metrics": {"total_missions": 3}}},
        ]
        series = build_metric_series(history, "missions", "total_missions")
        self.assertEqual(len(series), 2)
        self.assertEqual(series[1]["value"], 3)

    def test_delta_helper_calculates_changes(self) -> None:
        self.assertEqual(compute_delta(8, 3), 5.0)
        self.assertIsNone(compute_delta("x", 3))

    def test_status_trend_helper(self) -> None:
        history = [{"runtime": {"status": "healthy"}}, {"runtime": {"status": "warning"}}]
        trend = compute_status_trend(history, "runtime")
        self.assertEqual(trend["current"], "warning")
        self.assertTrue(trend["changed"])

    def test_recent_alert_summary(self) -> None:
        history = [{"generated_utc": "t1", "runtime": {"alerts": [{"level": "warning", "message": "x"}]}}]
        alerts = summarize_recent_alerts(history, limit=20)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["section"], "runtime")


if __name__ == "__main__":
    unittest.main()

