from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

from control_plane.contracts import ControlPlaneSnapshot, new_id as cp_new_id, utc_now as cp_utc_now, validate_control_plane_snapshot_dict
from lifecycle_manager.store import LifecycleStore
from memory_graph.store import MemoryGraphStore
from release_center.timeline_contracts import validate_release_timeline_report_dict
from release_gates.contracts import validate_gate_decision_dict
from release_readiness.contracts import validate_release_readiness_report_dict
from scheduler.store import SchedulerStateStore
from sentient_ui.contracts import PanelViewModel, ViewModelEnvelope, new_id as ui_new_id, utc_now as ui_utc_now, validate_view_model_envelope_dict


def bootstrap_advisory_artifacts(base_dir: str | Path = ".") -> Dict[str, Any]:
    root = Path(base_dir)
    created_or_updated: List[str] = []

    _ensure_dir(root / ".missions", created_or_updated)

    scheduler_store = SchedulerStateStore(state_path=root / ".scheduler" / "state.json")
    scheduler_state = scheduler_store.load_state()
    scheduler_store.save_state(scheduler_state)
    created_or_updated.append(str(scheduler_store.state_path))

    _bootstrap_governance_store(root / ".governance" / "repositories.json")
    created_or_updated.append(str(root / ".governance" / "repositories.json"))

    graph_store = MemoryGraphStore(graph_path=root / ".memory" / "graph.json")
    graph = graph_store.load_graph()
    graph_store.save_graph(graph)
    created_or_updated.append(str(root / ".memory" / "graph.json"))

    _ensure_dir(root / ".release_reports", created_or_updated)
    _bootstrap_release_readiness(root / ".release_reports" / "release_readiness.json")
    _bootstrap_gate_trace(root / ".release_reports" / "gate_trace.json")
    _bootstrap_release_timeline(root / ".release_reports" / "release_timeline.json")
    created_or_updated.extend(
        [
            str(root / ".release_reports" / "release_readiness.json"),
            str(root / ".release_reports" / "gate_trace.json"),
            str(root / ".release_reports" / "release_timeline.json"),
        ]
    )

    lifecycle_store = LifecycleStore(path=root / ".lifecycle" / "agents.json")
    lifecycle_state = lifecycle_store.load_state()
    lifecycle_store.save_state(lifecycle_state)
    created_or_updated.append(str(root / ".lifecycle" / "agents.json"))

    _bootstrap_control_plane_snapshot(root / ".control_plane" / "snapshot.json")
    created_or_updated.append(str(root / ".control_plane" / "snapshot.json"))

    _bootstrap_sentient_ui_view_model(root / ".sentient_ui" / "view_model.json")
    created_or_updated.append(str(root / ".sentient_ui" / "view_model.json"))

    return {
        "bootstrap_utc": cp_utc_now(),
        "advisory_only": True,
        "base_dir": str(root),
        "artifacts": created_or_updated,
    }


def _bootstrap_governance_store(path: Path) -> None:
    payload: Dict[str, Any] = {"schema_version": 1, "profiles": {}, "health_snapshots": {}, "audit_records": {}}
    _atomic_write_json(path, payload)


def _bootstrap_release_readiness(path: Path) -> None:
    payload = {
        "report_id": "release_readiness_bootstrap",
        "generated_utc": cp_utc_now(),
        "scope": "sentient-control-plane",
        "readiness_score": 100.0,
        "readiness_status": "ready",
        "blockers": [],
        "warnings": [],
        "findings": [],
        "checked_artifacts": [],
        "summary": {"note": "bootstrap-minimal"},
        "metadata": {"advisory_only": True, "bootstrap": True},
    }
    validate_release_readiness_report_dict(payload)
    _atomic_write_json(path, payload)


def _bootstrap_gate_trace(path: Path) -> None:
    decision = {
        "decision_id": "gate_decision_bootstrap",
        "policy_id": "default_gate_policy",
        "report_id": "release_readiness_bootstrap",
        "decision": "pass",
        "readiness_score": 100.0,
        "blockers": [],
        "warnings": [],
        "evaluated_artifacts": [],
        "created_utc": cp_utc_now(),
        "advisory_only": True,
        "metadata": {"bootstrap": True},
    }
    validate_gate_decision_dict(decision)
    payload = {
        "trace_id": "gate_trace_bootstrap",
        "decision": decision,
        "report_summary": {
            "report_id": "release_readiness_bootstrap",
            "readiness_score": 100.0,
            "readiness_status": "ready",
            "finding_count": 0,
        },
        "policy_summary": {
            "policy_id": "default_gate_policy",
            "minimum_readiness_score": 70,
            "advisory_only": True,
        },
        "metadata": {"advisory_only": True, "bootstrap": True},
    }
    _atomic_write_json(path, payload)


def _bootstrap_release_timeline(path: Path) -> None:
    payload = {
        "report_id": "release_timeline_bootstrap",
        "generated_utc": cp_utc_now(),
        "release_label": "bootstrap",
        "timeline_events": [],
        "milestones": [],
        "summary": {"event_count": 0, "milestone_count": 0},
        "escalation_hints": [],
        "advisory_only": True,
        "metadata": {"bootstrap": True},
    }
    validate_release_timeline_report_dict(payload)
    _atomic_write_json(path, payload)


def _bootstrap_control_plane_snapshot(path: Path) -> None:
    payload = ControlPlaneSnapshot(
        snapshot_id=cp_new_id("cp_snapshot_bootstrap"),
        generated_utc=cp_utc_now(),
        schema_version=1,
        runtime={},
        missions={},
        agents={},
        repositories={},
        tools={},
        scheduler={},
        memory_graph={},
        approvals={},
        consensus={},
        queue={},
        observability={},
        metadata={"bootstrap": True},
    ).to_dict()
    validate_control_plane_snapshot_dict(payload)
    _atomic_write_json(path, payload)


def _bootstrap_sentient_ui_view_model(path: Path) -> None:
    def panel(panel_id: str, title: str) -> Dict[str, Any]:
        return PanelViewModel(
            panel_id=panel_id,
            title=title,
            status="unknown",
            summary="bootstrap-minimal",
            metrics={},
            cards=[],
            tables=[],
            timelines=[],
            graph_nodes=[],
            graph_edges=[],
            alerts=[],
            metadata={"bootstrap": True},
        ).to_dict()

    payload = ViewModelEnvelope(
        view_model_id=ui_new_id("sentient_vm_bootstrap"),
        generated_utc=ui_utc_now(),
        source_snapshot_id="cp_snapshot_bootstrap",
        schema_version=1,
        runtime_panel=panel("runtime", "Runtime"),
        mission_panel=panel("missions", "Missions"),
        agent_panel=panel("agents", "Agents"),
        repository_panel=panel("repositories", "Repositories"),
        tool_panel=panel("tools", "Tools"),
        scheduler_panel=panel("scheduler", "Scheduler"),
        memory_panel=panel("memory", "Memory"),
        approval_panel=panel("approvals", "Approvals"),
        consensus_panel=panel("consensus", "Consensus"),
        observability_panel=panel("observability", "Observability"),
        alerts=[],
        metadata={"bootstrap": True},
    ).to_dict()
    validate_view_model_envelope_dict(payload)
    _atomic_write_json(path, payload)


def _ensure_dir(path: Path, touched: List[str]) -> None:
    path.mkdir(parents=True, exist_ok=True)
    touched.append(str(path))


def _atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(tmp_path, path)

