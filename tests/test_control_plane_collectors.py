from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from control_plane.collectors import (  # noqa: E402
    collect_approval_consensus_summary,
    collect_memory_graph_summary,
    collect_mission_summary,
    collect_observability_summary,
    collect_registry_summary,
    collect_repository_governance_summary,
    collect_runtime_status,
    collect_scheduler_summary,
)


class TestControlPlaneCollectors(unittest.TestCase):
    def test_collectors_handle_missing_files_gracefully(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.assertIsInstance(collect_runtime_status(base), dict)
            self.assertEqual(collect_mission_summary(base)["total_missions"], 0)
            self.assertEqual(collect_repository_governance_summary(base)["profile_count"], 0)
            self.assertEqual(collect_scheduler_summary(base)["worker_count"], 0)
            self.assertEqual(collect_memory_graph_summary(base)["node_count"], 0)
            self.assertEqual(collect_observability_summary(base)["error_count"], 0)

    def test_collectors_count_sample_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / ".missions").mkdir(parents=True, exist_ok=True)
            (base / ".missions" / "mission_a.json").write_text(
                json.dumps(
                    {
                        "mission_id": "mission_a",
                        "title": "A",
                        "instruction": "Do A",
                        "target_repository": "ConceptSHOP",
                        "target_repositories": ["ConceptSHOP"],
                        "priority": 1,
                        "status": "scheduled",
                        "risk_tier": "standard",
                        "created_utc": "2026-01-01T00:00:00Z",
                        "updated_utc": "2026-01-01T00:00:00Z",
                        "tasks": [
                            {
                                "task_id": "task_a",
                                "mission_id": "mission_a",
                                "instruction": "Do task",
                                "status": "queued",
                                "required_tools": [],
                                "depends_on": [],
                                "priority": 1,
                                "created_utc": "2026-01-01T00:00:00Z",
                                "updated_utc": "2026-01-01T00:00:00Z",
                            }
                        ],
                        "approvals": [{"approval_id": "a1", "status": "approved", "action": "approve"}],
                        "consensus_records": [{"consensus_id": "c1", "consensus_type": "twin", "decision": "approved"}],
                        "telemetry_events": [],
                        "artifacts": [],
                        "failure_reason": None,
                    }
                ),
                encoding="utf-8",
            )
            (base / ".governance").mkdir(parents=True, exist_ok=True)
            (base / ".governance" / "repositories.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "profiles": {"ConceptSHOP": {"repository_name": "ConceptSHOP"}},
                        "health_snapshots": {"ConceptSHOP": [{"warnings": ["w1"], "errors": ["e1"]}]},
                        "audit_records": {"ConceptSHOP": [{"audit_id": "r1"}]},
                    }
                ),
                encoding="utf-8",
            )
            (base / ".scheduler").mkdir(parents=True, exist_ok=True)
            (base / ".scheduler" / "state.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "workers": {"w1": {"status": "idle"}, "w2": {"status": "busy"}},
                        "leases": {"l1": {"lease_status": "active"}, "l2": {"lease_status": "released"}},
                        "scheduler_events": [],
                    }
                ),
                encoding="utf-8",
            )
            (base / ".memory").mkdir(parents=True, exist_ok=True)
            (base / ".memory" / "graph.json").write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "nodes": {"n1": {"node_type": "mission"}, "n2": {"node_type": "task"}},
                        "edges": {"e1": {"edge_type": "contains"}},
                    }
                ),
                encoding="utf-8",
            )
            (base / ".logs").mkdir(parents=True, exist_ok=True)
            (base / ".logs" / "errors.json").write_text(json.dumps({"errors": [{"message": "x"}]}), encoding="utf-8")

            mission = collect_mission_summary(base)
            self.assertEqual(mission["total_missions"], 1)
            self.assertEqual(mission["task_status_counts"]["queued"], 1)
            gov = collect_repository_governance_summary(base)
            self.assertEqual(gov["profile_count"], 1)
            self.assertEqual(gov["warning_count"], 1)
            sched = collect_scheduler_summary(base)
            self.assertEqual(sched["worker_status_counts"]["idle"], 1)
            self.assertEqual(sched["active_leases"], 1)
            graph = collect_memory_graph_summary(base)
            self.assertEqual(graph["node_count"], 2)
            approv = collect_approval_consensus_summary(base)
            self.assertEqual(approv["approval_status_counts"]["approved"], 1)
            self.assertEqual(approv["consensus_type_counts"]["twin"], 1)

    def test_registry_summary_reads_repo_configs(self) -> None:
        summary = collect_registry_summary(REPO_ROOT)
        self.assertIn("canonical", summary)
        self.assertIn("legacy", summary)
        self.assertGreaterEqual(summary["canonical"]["repositories"], 1)


if __name__ == "__main__":
    unittest.main()

