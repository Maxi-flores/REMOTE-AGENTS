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

from sentient_ui.contracts import validate_panel_view_model_dict, validate_view_model_envelope_dict  # noqa: E402
from sentient_ui.view_models import (  # noqa: E402
    build_agent_panel,
    build_approval_panel,
    build_consensus_panel,
    build_memory_panel,
    build_mission_panel,
    build_observability_panel,
    build_repository_panel,
    build_runtime_panel,
    build_scheduler_panel,
    build_sentient_view_model,
    build_tool_panel,
)


def _snapshot() -> dict:
    return {
        "snapshot_id": "snap_1",
        "generated_utc": "2026-01-01T00:00:00Z",
        "runtime": {"status": "warning", "summary": "runtime", "metrics": {"queue_occupied": True, "lock_present": True, "state": "queue_slot_occupied"}},
        "missions": {"status": "healthy", "summary": "missions", "metrics": {"total_missions": 2, "mission_status_counts": {"scheduled": 1}, "task_status_counts": {"queued": 1}}, "records": [{"mission_id": "m1"}]},
        "agents": {"status": "healthy", "summary": "agents", "metrics": {"canonical_agents": 12}},
        "repositories": {"status": "warning", "summary": "repositories", "metrics": {"canonical_repositories": 10, "governance_profiles": 8, "health_snapshots": 0}},
        "tools": {"status": "healthy", "summary": "tools", "metrics": {"routed_tools": 6, "canonical_tools": 6, "provider_counts": {"mcp": 4}, "risk_counts": {"high": 2}}},
        "scheduler": {"status": "healthy", "summary": "scheduler", "metrics": {"worker_count": 2, "active_leases": 1}},
        "memory_graph": {"status": "healthy", "summary": "memory", "metrics": {"node_count": 5, "edge_count": 4, "node_type_counts": {"mission": 1}, "edge_type_counts": {"contains": 1}}},
        "approvals": {"status": "healthy", "summary": "approvals", "metrics": {"approval_status_counts": {"requested": 1}, "approval_action_counts": {"approve": 2}}},
        "consensus": {"status": "healthy", "summary": "consensus", "metrics": {"consensus_type_counts": {"twin": 2}, "consensus_decision_counts": {"rejected": 1}}},
        "queue": {"status": "warning", "summary": "queue", "metrics": {"state": "queue_slot_occupied", "queue_occupied": True, "lock_present": True}},
        "observability": {"status": "warning", "summary": "obs", "metrics": {"error_count": 3, "consensus_metrics_keys": 2}},
    }


class TestSentientUiViewModels(unittest.TestCase):
    def test_all_panel_builders_return_valid_panels(self) -> None:
        snapshot = _snapshot()
        panels = [
            build_runtime_panel(snapshot),
            build_mission_panel(snapshot),
            build_agent_panel(snapshot),
            build_repository_panel(snapshot),
            build_tool_panel(snapshot),
            build_scheduler_panel(snapshot),
            build_memory_panel(snapshot),
            build_approval_panel(snapshot),
            build_consensus_panel(snapshot),
            build_observability_panel(snapshot),
        ]
        for panel in panels:
            validate_panel_view_model_dict(panel)

    def test_full_view_model_includes_all_panels(self) -> None:
        history = [dict(_snapshot())]
        model = build_sentient_view_model(_snapshot(), history=history)
        validate_view_model_envelope_dict(model)
        for key in (
            "runtime_panel",
            "mission_panel",
            "agent_panel",
            "repository_panel",
            "tool_panel",
            "scheduler_panel",
            "memory_panel",
            "approval_panel",
            "consensus_panel",
            "observability_panel",
        ):
            self.assertIn(key, model)
            self.assertIsInstance(model[key], dict)


if __name__ == "__main__":
    unittest.main()

