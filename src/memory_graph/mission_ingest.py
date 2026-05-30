from __future__ import annotations

from typing import Any

from mission_engine.contracts import ApprovalRecord, ConsensusRecord, Mission, MissionTask

from .contracts import create_edge, create_node
from .store import MemoryGraphStore


SOURCE = "mission-ingest"


def repository_node_id(repository_name: str) -> str:
    return f"repository:{repository_name}"


def mission_node_id(mission_id: str) -> str:
    return f"mission:{mission_id}"


def task_node_id(task_id: str) -> str:
    return f"task:{task_id}"


def agent_node_id(agent_class: str) -> str:
    return f"agent:{agent_class}"


def tool_node_id(tool_name: str) -> str:
    return f"tool:{tool_name}"


def approval_node_id(approval_id: str) -> str:
    return f"approval:{approval_id}"


def consensus_node_id(consensus_id: str) -> str:
    return f"consensus:{consensus_id}"


def ingest_mission(mission: Mission | dict[str, Any], *, store: MemoryGraphStore | None = None) -> MemoryGraphStore:
    graph = store or MemoryGraphStore()
    obj = Mission.from_dict(mission) if isinstance(mission, dict) else mission
    graph.upsert_node(
        create_node(
            node_id=mission_node_id(obj.mission_id),
            node_type="mission",
            label=obj.title,
            source=SOURCE,
            metadata={
                "mission_id": obj.mission_id,
                "status": obj.status,
                "risk_tier": obj.risk_tier,
                "priority": obj.priority,
                "instruction": obj.instruction,
            },
        )
    )
    for repo in obj.target_repositories:
        _upsert_repository(graph, repo)
        graph.upsert_edge(
            create_edge(
                from_node_id=mission_node_id(obj.mission_id),
                to_node_id=repository_node_id(repo),
                edge_type="targets_repository",
                source=SOURCE,
            )
        )
    if obj.failure_reason:
        incident_id = f"incident:{obj.mission_id}:failure"
        graph.upsert_node(
            create_node(
                node_id=incident_id,
                node_type="incident",
                label=f"{obj.title} failure",
                source=SOURCE,
                metadata={"failure_reason": obj.failure_reason, "mission_id": obj.mission_id},
            )
        )
        graph.upsert_edge(
            create_edge(
                from_node_id=mission_node_id(obj.mission_id),
                to_node_id=incident_id,
                edge_type="remembered_as",
                source=SOURCE,
            )
        )
    if obj.status == "completed":
        decision_id = f"decision:{obj.mission_id}:completed"
        graph.upsert_node(
            create_node(
                node_id=decision_id,
                node_type="decision",
                label=f"{obj.title} completed",
                source=SOURCE,
                metadata={"mission_id": obj.mission_id, "status": obj.status},
            )
        )
        graph.upsert_edge(
            create_edge(
                from_node_id=mission_node_id(obj.mission_id),
                to_node_id=decision_id,
                edge_type="remembered_as",
                source=SOURCE,
            )
        )
    return graph


def ingest_task(mission_id: str, task: MissionTask | dict[str, Any], *, store: MemoryGraphStore | None = None) -> MemoryGraphStore:
    graph = store or MemoryGraphStore()
    obj = MissionTask.from_dict(task) if isinstance(task, dict) else task
    graph.upsert_node(
        create_node(
            node_id=task_node_id(obj.task_id),
            node_type="task",
            label=obj.instruction[:120],
            source=SOURCE,
            metadata={
                "task_id": obj.task_id,
                "mission_id": obj.mission_id,
                "status": obj.status,
                "priority": obj.priority,
            },
        )
    )
    graph.upsert_edge(
        create_edge(
            from_node_id=mission_node_id(mission_id),
            to_node_id=task_node_id(obj.task_id),
            edge_type="contains",
            source=SOURCE,
        )
    )
    if obj.target_repository:
        _upsert_repository(graph, obj.target_repository)
        graph.upsert_edge(
            create_edge(
                from_node_id=task_node_id(obj.task_id),
                to_node_id=repository_node_id(obj.target_repository),
                edge_type="targets_repository",
                source=SOURCE,
            )
        )
    if obj.assigned_primary_agent:
        _upsert_agent(graph, obj.assigned_primary_agent)
        graph.upsert_edge(
            create_edge(
                from_node_id=task_node_id(obj.task_id),
                to_node_id=agent_node_id(obj.assigned_primary_agent),
                edge_type="assigned_to",
                source=SOURCE,
            )
        )
    if obj.assigned_twin_agent:
        _upsert_agent(graph, obj.assigned_twin_agent)
        graph.upsert_edge(
            create_edge(
                from_node_id=task_node_id(obj.task_id),
                to_node_id=agent_node_id(obj.assigned_twin_agent),
                edge_type="reviewed_by",
                source=SOURCE,
            )
        )
    for tool in obj.required_tools:
        graph.upsert_node(create_node(node_id=tool_node_id(tool), node_type="tool", label=tool, source=SOURCE))
        graph.upsert_edge(
            create_edge(
                from_node_id=task_node_id(obj.task_id),
                to_node_id=tool_node_id(tool),
                edge_type="uses_tool",
                source=SOURCE,
            )
        )
    for dep in obj.depends_on:
        graph.upsert_edge(
            create_edge(
                from_node_id=task_node_id(obj.task_id),
                to_node_id=task_node_id(dep),
                edge_type="depends_on",
                source=SOURCE,
            )
        )
    return graph


def ingest_approval(
    mission_id: str,
    approval_record: ApprovalRecord | dict[str, Any],
    *,
    store: MemoryGraphStore | None = None,
) -> MemoryGraphStore:
    graph = store or MemoryGraphStore()
    obj = ApprovalRecord.from_dict(approval_record) if isinstance(approval_record, dict) else approval_record
    graph.upsert_node(
        create_node(
            node_id=approval_node_id(obj.approval_id),
            node_type="approval",
            label=f"{obj.action}:{obj.status}",
            source=SOURCE,
            metadata=obj.to_dict(),
        )
    )
    graph.upsert_edge(
        create_edge(
            from_node_id=mission_node_id(mission_id),
            to_node_id=approval_node_id(obj.approval_id),
            edge_type="contains",
            source=SOURCE,
        )
    )
    actor = obj.reviewed_by or obj.requested_by
    if actor:
        _upsert_agent(graph, actor)
        edge_type = "approved_by" if obj.status == "approved" else "rejected_by" if obj.status == "rejected" else "reviewed_by"
        graph.upsert_edge(
            create_edge(
                from_node_id=approval_node_id(obj.approval_id),
                to_node_id=agent_node_id(actor),
                edge_type=edge_type,
                source=SOURCE,
            )
        )
    return graph


def ingest_consensus(
    mission_id: str,
    consensus_record: ConsensusRecord | dict[str, Any],
    *,
    store: MemoryGraphStore | None = None,
) -> MemoryGraphStore:
    graph = store or MemoryGraphStore()
    obj = ConsensusRecord.from_dict(consensus_record) if isinstance(consensus_record, dict) else consensus_record
    graph.upsert_node(
        create_node(
            node_id=consensus_node_id(obj.consensus_id),
            node_type="consensus",
            label=f"{obj.consensus_type}:{obj.decision}",
            source=SOURCE,
            metadata=obj.to_dict(),
        )
    )
    graph.upsert_edge(
        create_edge(
            from_node_id=mission_node_id(mission_id),
            to_node_id=consensus_node_id(obj.consensus_id),
            edge_type="contains",
            source=SOURCE,
        )
    )
    actor = obj.agent_class or obj.actor
    _upsert_agent(graph, actor)
    graph.upsert_edge(
        create_edge(
            from_node_id=consensus_node_id(obj.consensus_id),
            to_node_id=agent_node_id(actor),
            edge_type="reviewed_by",
            source=SOURCE,
        )
    )
    return graph


def ingest_mission_snapshot(mission: Mission | dict[str, Any], *, store: MemoryGraphStore | None = None) -> MemoryGraphStore:
    graph = store or MemoryGraphStore()
    obj = Mission.from_dict(mission) if isinstance(mission, dict) else mission
    ingest_mission(obj, store=graph)
    for task in obj.tasks:
        ingest_task(obj.mission_id, task, store=graph)
    for approval in obj.approvals:
        ingest_approval(obj.mission_id, approval, store=graph)
    for consensus in obj.consensus_records:
        ingest_consensus(obj.mission_id, consensus, store=graph)
    for artifact in obj.artifacts:
        if not isinstance(artifact, dict):
            continue
        artifact_id = str(artifact.get("artifact_id") or artifact.get("path") or artifact.get("name") or "")
        if not artifact_id:
            continue
        node_id = f"artifact:{artifact_id}"
        graph.upsert_node(create_node(node_id=node_id, node_type="artifact", label=artifact_id, source=SOURCE, metadata=artifact))
        graph.upsert_edge(
            create_edge(
                from_node_id=mission_node_id(obj.mission_id),
                to_node_id=node_id,
                edge_type="produced_artifact",
                source=SOURCE,
            )
        )
    return graph


def _upsert_repository(graph: MemoryGraphStore, repository_name: str) -> None:
    graph.upsert_node(
        create_node(
            node_id=repository_node_id(repository_name),
            node_type="repository",
            label=repository_name,
            source=SOURCE,
            metadata={"repository_name": repository_name},
        )
    )


def _upsert_agent(graph: MemoryGraphStore, agent_class: str) -> None:
    graph.upsert_node(
        create_node(
            node_id=agent_node_id(agent_class),
            node_type="agent",
            label=agent_class,
            source=SOURCE,
            metadata={"agent_class": agent_class},
        )
    )

