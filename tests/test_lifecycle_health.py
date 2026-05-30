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

from lifecycle_manager.control_plane_adapter import collect_lifecycle_summary  # noqa: E402
from lifecycle_manager.health import (  # noqa: E402
    calculate_repository_coverage,
    detect_capability_gaps,
    detect_single_points_of_failure,
)
from lifecycle_manager.sentient_ui_adapter import (  # noqa: E402
    build_agent_capability_matrix_panel,
    build_lifecycle_status_panel,
    build_repository_coverage_panel,
)


class TestLifecycleHealth(unittest.TestCase):
    def test_health_gap_and_spof_detection(self) -> None:
        repos = {"repositories": [{"name": "Repo1"}, {"name": "Repo2"}]}
        profiles = [{"agent_class": "A1", "repositories": ["Repo1"], "primary_roles": ["Repo1"], "secondary_roles": []}]
        gaps = detect_capability_gaps(repos, profiles)
        self.assertTrue(any(g["repository_name"] == "Repo2" for g in gaps))
        spof = detect_single_points_of_failure(profiles)
        self.assertTrue(any(r["repository_name"] == "Repo1" for r in spof))
        cov = calculate_repository_coverage("Repo1", profiles)
        self.assertIn("A1", cov["primary_coverage"])

    def test_optional_adapters_work(self) -> None:
        profiles = [{"agent_class": "A1", "repositories": ["Repo1"], "status": "active", "risk_tier": "medium"}]
        states = [{"agent_id": "id1", "agent_class": "A1", "status": "active", "health": "healthy", "availability": "available"}]
        panel1 = build_agent_capability_matrix_panel(profiles)
        panel2 = build_lifecycle_status_panel(states)
        panel3 = build_repository_coverage_panel(profiles)
        self.assertEqual(panel1["panel_id"], "agent_capability_matrix_panel")
        self.assertEqual(panel2["panel_id"], "lifecycle_status_panel")
        self.assertEqual(panel3["panel_id"], "repository_coverage_panel")
        summary = collect_lifecycle_summary(REPO_ROOT)
        self.assertIn("capability_profile_count", summary)


if __name__ == "__main__":
    unittest.main()

