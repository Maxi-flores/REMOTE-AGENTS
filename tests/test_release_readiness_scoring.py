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

from release_readiness.scoring import build_release_readiness_report, classify_readiness, score_findings  # noqa: E402


class TestReleaseReadinessScoring(unittest.TestCase):
    def test_score_findings_deducts_expected_points(self) -> None:
        findings = [
            {"severity": "warning", "drift_type": "compatibility_warning", "message": "warn"},
            {"severity": "error", "drift_type": "missing_required_field", "message": "err"},
        ]
        scored = score_findings(findings)
        self.assertEqual(scored["score"], 75.0)

    def test_critical_finding_creates_blocker(self) -> None:
        findings = [{"severity": "critical", "drift_type": "unsupported_version", "message": "critical"}]
        scored = score_findings(findings)
        self.assertGreaterEqual(len(scored["blockers"]), 1)

    def test_readiness_status_follows_scoring_rules(self) -> None:
        self.assertEqual(classify_readiness(95, []), "ready")
        self.assertEqual(classify_readiness(80, []), "ready_with_warnings")
        self.assertEqual(classify_readiness(60, []), "blocked")
        self.assertEqual(classify_readiness(95, ["x"]), "blocked")

    def test_build_release_readiness_report(self) -> None:
        report = build_release_readiness_report(
            findings=[{"severity": "warning", "drift_type": "compatibility_warning", "message": "warn"}],
            checked_artifacts=[{"artifact_type": "control_plane_snapshot"}],
        )
        self.assertIn("readiness_score", report)
        self.assertIn("readiness_status", report)


if __name__ == "__main__":
    unittest.main()

