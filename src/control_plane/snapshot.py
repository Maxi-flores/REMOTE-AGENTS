from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

from control_plane.collectors import (
    collect_approval_consensus_summary,
    collect_memory_graph_summary,
    collect_mission_summary,
    collect_observability_summary,
    collect_registry_summary,
    collect_repository_governance_summary,
    collect_runtime_status,
    collect_scheduler_summary,
    collect_tool_router_summary,
)
from control_plane.contracts import (
    ControlPlaneSnapshot,
    DashboardSection,
    new_id,
    utc_now,
    validate_control_plane_snapshot_dict,
)


def build_control_plane_snapshot(base_dir: str | Path = ".") -> Dict[str, Any]:
    runtime = collect_runtime_status(base_dir)
    mission = collect_mission_summary(base_dir)
    registry = collect_registry_summary(base_dir)
    governance = collect_repository_governance_summary(base_dir)
    scheduler = collect_scheduler_summary(base_dir)
    tool_router = collect_tool_router_summary(base_dir)
    memory = collect_memory_graph_summary(base_dir)
    approvals_consensus = collect_approval_consensus_summary(base_dir)
    observability = collect_observability_summary(base_dir)

    snapshot = ControlPlaneSnapshot(
        snapshot_id=new_id("control_plane_snapshot"),
        generated_utc=utc_now(),
        schema_version=1,
        runtime=_section(
            "runtime",
            "Runtime",
            "healthy" if runtime.get("state") == "queue_available" else "warning",
            "Local runtime and queue lock state.",
            metrics=runtime,
        ),
        missions=_section(
            "missions",
            "Missions",
            "healthy",
            "Mission and task status distribution.",
            metrics={
                "total_missions": mission.get("total_missions", 0),
                "mission_status_counts": mission.get("mission_status_counts", {}),
                "task_status_counts": mission.get("task_status_counts", {}),
            },
            records=mission.get("recent_missions", []),
        ),
        agents=_section(
            "agents",
            "Agents",
            "healthy",
            "Agent registry presence summary.",
            metrics={"canonical_agents": registry.get("canonical", {}).get("agents", 0)},
        ),
        repositories=_section(
            "repositories",
            "Repositories",
            "healthy",
            "Repository registry and governance profile summary.",
            metrics={
                "canonical_repositories": registry.get("canonical", {}).get("repositories", 0),
                "governance_profiles": governance.get("profile_count", 0),
                "health_snapshots": governance.get("health_snapshot_count", 0),
            },
        ),
        tools=_section(
            "tools",
            "Tools",
            "healthy",
            "Canonical tools, legacy tools, and routed tool metadata summary.",
            metrics={
                "canonical_tools": registry.get("canonical", {}).get("tools", 0),
                "legacy_platform_tools": registry.get("legacy", {}).get("platform_mcp_tools", 0),
                "routed_tools": tool_router.get("tool_count", 0),
                "provider_counts": tool_router.get("provider_counts", {}),
                "risk_counts": tool_router.get("risk_counts", {}),
            },
        ),
        scheduler=_section(
            "scheduler",
            "Scheduler",
            "healthy",
            "Worker and lease metadata summary.",
            metrics=scheduler,
        ),
        memory_graph=_section(
            "memory_graph",
            "Memory Graph",
            "healthy",
            "Local semantic memory graph size summary.",
            metrics=memory,
        ),
        approvals=_section(
            "approvals",
            "Approvals",
            "healthy",
            "Mission-level approval status and action counts.",
            metrics={
                "approval_status_counts": approvals_consensus.get("approval_status_counts", {}),
                "approval_action_counts": approvals_consensus.get("approval_action_counts", {}),
            },
        ),
        consensus=_section(
            "consensus",
            "Consensus",
            "healthy",
            "Mission-level consensus type and decision counts.",
            metrics={
                "consensus_type_counts": approvals_consensus.get("consensus_type_counts", {}),
                "consensus_decision_counts": approvals_consensus.get("consensus_decision_counts", {}),
            },
        ),
        queue=_section(
            "queue",
            "Queue",
            "healthy" if runtime.get("queue_occupied") is False else "warning",
            "Legacy single-file queue state summary.",
            metrics={
                "queue_occupied": runtime.get("queue_occupied", False),
                "lock_present": runtime.get("lock_present", False),
                "state": runtime.get("state", "unknown"),
            },
        ),
        observability=_section(
            "observability",
            "Observability",
            "warning" if observability.get("error_count", 0) > 0 else "healthy",
            "Consensus metrics and error-log summary.",
            metrics=observability,
        ),
        metadata={
            "read_only_sources": True,
            "writes_outside_control_plane": False,
            "base_dir": str(Path(base_dir)),
        },
    ).to_dict()
    validate_control_plane_snapshot_dict(snapshot)
    return snapshot


def export_control_plane_snapshot(
    path: str | Path = ".control_plane/snapshot.json",
    *,
    base_dir: str | Path = ".",
) -> Dict[str, Any]:
    snapshot = build_control_plane_snapshot(base_dir=base_dir)
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_name(f".{out_path.name}.tmp")
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp_path, out_path)
    return snapshot


def export_control_plane_snapshot_jsonl(
    path: str | Path = ".control_plane/snapshots.jsonl",
    *,
    base_dir: str | Path = ".",
) -> Dict[str, Any]:
    snapshot = build_control_plane_snapshot(base_dir=base_dir)
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(snapshot, sort_keys=True))
        f.write("\n")
    return snapshot


def _section(
    section_id: str,
    title: str,
    status: str,
    summary: str,
    *,
    metrics: Dict[str, Any] | None = None,
    records: list[Dict[str, Any]] | None = None,
    warnings: list[str] | None = None,
    errors: list[str] | None = None,
    metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    return DashboardSection(
        section_id=section_id,
        title=title,
        status=status,  # type: ignore[arg-type]
        summary=summary,
        metrics=dict(metrics or {}),
        records=list(records or []),
        warnings=list(warnings or []),
        errors=list(errors or []),
        metadata=dict(metadata or {}),
    ).to_dict()

