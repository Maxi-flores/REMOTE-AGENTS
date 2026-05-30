from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable

from scheduler.queue_compat import explain_queue_backpressure
from tool_router.router import list_tool_routes


def collect_runtime_status(base_dir: str | Path = ".") -> Dict[str, Any]:
    root = Path(base_dir)
    queue_path = root / ".platform_queue" / "next_task.json"
    lock_path = root / ".platform_queue" / "processing.lock"
    backpressure = explain_queue_backpressure(queue_path, lock_path)
    return {
        "queue_occupied": backpressure["queue_occupied"],
        "lock_present": backpressure["lock_present"],
        "state": backpressure["state"],
        "queue_path": str(queue_path),
        "lock_path": str(lock_path),
    }


def collect_mission_summary(base_dir: str | Path = ".") -> Dict[str, Any]:
    root = Path(base_dir)
    missions_dir = root / ".missions"
    mission_status_counts: Counter[str] = Counter()
    task_status_counts: Counter[str] = Counter()
    recent: list[dict[str, Any]] = []
    for mission in _iter_mission_objects(missions_dir):
        status = str(mission.get("status") or "unknown")
        mission_status_counts[status] += 1
        tasks = mission.get("tasks") if isinstance(mission.get("tasks"), list) else []
        for task in tasks:
            if isinstance(task, dict):
                task_status_counts[str(task.get("status") or "unknown")] += 1
        recent.append(
            {
                "mission_id": mission.get("mission_id"),
                "title": mission.get("title"),
                "status": status,
                "updated_utc": mission.get("updated_utc"),
                "task_count": len(tasks),
            }
        )
    recent.sort(key=lambda item: str(item.get("updated_utc") or ""), reverse=True)
    return {
        "total_missions": sum(mission_status_counts.values()),
        "mission_status_counts": dict(mission_status_counts),
        "task_status_counts": dict(task_status_counts),
        "recent_missions": recent[:10],
    }


def collect_registry_summary(base_dir: str | Path = ".") -> Dict[str, Any]:
    root = Path(base_dir)
    registries = root / "config" / "registries"
    repositories = _load_json_object(registries / "repositories.json").get("repositories", [])
    agents = _load_json_object(registries / "agents.json").get("agents", [])
    tools = _load_json_object(registries / "tools.json").get("tools", [])
    models = _load_json_object(registries / "models.json").get("models", [])
    policies = _load_json_object(registries / "policies.json").get("policies", [])
    legacy_agents = _load_json_object(root / "config" / "agent_registry.json")
    legacy_tools = _load_json_object(root / "config" / "platform_mcp_tools.json").get("tools", [])
    return {
        "canonical": {
            "repositories": len(repositories) if isinstance(repositories, list) else 0,
            "agents": len(agents) if isinstance(agents, list) else 0,
            "tools": len(tools) if isinstance(tools, list) else 0,
            "models": len(models) if isinstance(models, list) else 0,
            "policies": len(policies) if isinstance(policies, list) else 0,
        },
        "legacy": {
            "agent_registry_keys": len(legacy_agents.keys()) if isinstance(legacy_agents, dict) else 0,
            "platform_mcp_tools": len(legacy_tools) if isinstance(legacy_tools, list) else 0,
        },
    }


def collect_repository_governance_summary(base_dir: str | Path = ".") -> Dict[str, Any]:
    state = _load_json_object(Path(base_dir) / ".governance" / "repositories.json")
    profiles = state.get("profiles") if isinstance(state.get("profiles"), dict) else {}
    health = state.get("health_snapshots") if isinstance(state.get("health_snapshots"), dict) else {}
    audits = state.get("audit_records") if isinstance(state.get("audit_records"), dict) else {}
    warning_count = 0
    error_count = 0
    for snapshots in health.values():
        if isinstance(snapshots, list):
            for snapshot in snapshots:
                if isinstance(snapshot, dict):
                    warning_count += len(snapshot.get("warnings") or [])
                    error_count += len(snapshot.get("errors") or [])
    return {
        "profile_count": len(profiles),
        "health_snapshot_count": sum(len(v) for v in health.values() if isinstance(v, list)),
        "audit_record_count": sum(len(v) for v in audits.values() if isinstance(v, list)),
        "warning_count": warning_count,
        "error_count": error_count,
    }


def collect_scheduler_summary(base_dir: str | Path = ".") -> Dict[str, Any]:
    state = _load_json_object(Path(base_dir) / ".scheduler" / "state.json")
    workers = state.get("workers") if isinstance(state.get("workers"), dict) else {}
    leases = state.get("leases") if isinstance(state.get("leases"), dict) else {}
    worker_status = Counter()
    lease_status = Counter()
    for worker in workers.values():
        if isinstance(worker, dict):
            worker_status[str(worker.get("status") or "unknown")] += 1
    for lease in leases.values():
        if isinstance(lease, dict):
            lease_status[str(lease.get("lease_status") or "unknown")] += 1
    return {
        "worker_count": len(workers),
        "worker_status_counts": dict(worker_status),
        "lease_count": len(leases),
        "lease_status_counts": dict(lease_status),
        "active_leases": lease_status.get("active", 0) + lease_status.get("renewed", 0),
        "expired_leases": lease_status.get("expired", 0),
        "released_leases": lease_status.get("released", 0),
    }


def collect_tool_router_summary(base_dir: str | Path = ".") -> Dict[str, Any]:
    _ = base_dir  # reserved for future path-aware adapters
    routes = list_tool_routes()
    by_provider = Counter(route.provider for route in routes)
    by_risk = Counter(route.risk_tier for route in routes)
    by_approval = Counter("approval_required" if route.approval_required else "no_approval_required" for route in routes)
    return {
        "tool_count": len(routes),
        "provider_counts": dict(by_provider),
        "risk_counts": dict(by_risk),
        "approval_counts": dict(by_approval),
    }


def collect_memory_graph_summary(base_dir: str | Path = ".") -> Dict[str, Any]:
    graph = _load_json_object(Path(base_dir) / ".memory" / "graph.json")
    nodes = graph.get("nodes") if isinstance(graph.get("nodes"), dict) else {}
    edges = graph.get("edges") if isinstance(graph.get("edges"), dict) else {}
    node_types = Counter()
    edge_types = Counter()
    for node in nodes.values():
        if isinstance(node, dict):
            node_types[str(node.get("node_type") or "unknown")] += 1
    for edge in edges.values():
        if isinstance(edge, dict):
            edge_types[str(edge.get("edge_type") or "unknown")] += 1
    return {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "node_type_counts": dict(node_types),
        "edge_type_counts": dict(edge_types),
    }


def collect_approval_consensus_summary(base_dir: str | Path = ".") -> Dict[str, Any]:
    approvals_by_status = Counter()
    approvals_by_action = Counter()
    consensus_by_type = Counter()
    consensus_by_decision = Counter()
    for mission in _iter_mission_objects(Path(base_dir) / ".missions"):
        approvals = mission.get("approvals") if isinstance(mission.get("approvals"), list) else []
        consensus = mission.get("consensus_records") if isinstance(mission.get("consensus_records"), list) else []
        for approval in approvals:
            if isinstance(approval, dict):
                approvals_by_status[str(approval.get("status") or "unknown")] += 1
                approvals_by_action[str(approval.get("action") or "unknown")] += 1
        for record in consensus:
            if isinstance(record, dict):
                consensus_by_type[str(record.get("consensus_type") or "unknown")] += 1
                consensus_by_decision[str(record.get("decision") or "unknown")] += 1
    return {
        "approval_status_counts": dict(approvals_by_status),
        "approval_action_counts": dict(approvals_by_action),
        "consensus_type_counts": dict(consensus_by_type),
        "consensus_decision_counts": dict(consensus_by_decision),
    }


def collect_observability_summary(base_dir: str | Path = ".") -> Dict[str, Any]:
    root = Path(base_dir)
    consensus_metrics = _load_json_object(root / ".logs" / "consensus_metrics.json")
    errors_obj = _load_json_object(root / ".logs" / "errors.json")
    errors: list[Any]
    if isinstance(errors_obj.get("errors"), list):
        errors = errors_obj["errors"]
    elif isinstance(errors_obj, list):
        errors = errors_obj
    else:
        errors = []
    return {
        "consensus_metrics_keys": len(consensus_metrics.keys()) if isinstance(consensus_metrics, dict) else 0,
        "error_count": len(errors),
    }


def _iter_mission_objects(missions_dir: Path) -> Iterable[Dict[str, Any]]:
    if not missions_dir.exists():
        return []
    objects: list[Dict[str, Any]] = []
    for path in sorted(missions_dir.glob("*.json")):
        data = _load_json_object(path)
        if data:
            objects.append(data)
    return objects


def _load_json_object(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}

