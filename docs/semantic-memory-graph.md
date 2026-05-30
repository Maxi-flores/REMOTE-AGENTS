# Semantic Memory Graph MVP

Phase 4 adds a local Semantic Memory Graph MVP for mission facts.

## Purpose

The graph is a seed memory structure for Sentient OS. It records mission, task, repository, agent, tool, approval, consensus, artifact, incident, decision, policy, and model facts as nodes and relationships.

It is intended to become the basis for a future Sentient OS Memory Graph UI.

## Compatibility Boundary

This graph does not replace the existing semantic memory behavior.

- `.logs/semantic_memory.json` stays active.
- `platform_engine.py` memory injection stays unchanged.
- Graph ingestion is optional.
- Graph retrieval is not required at runtime.
- There is no database, vector database, daemon, network service, or scheduler dependency.

Future phases may connect graph memory to the planner, agents, runtime policy checks, and Sentient OS visualization.

## Storage

The graph is stored at:

```text
.memory/graph.json
```

Shape:

```json
{
  "schema_version": 1,
  "nodes": {},
  "edges": {}
}
```

Writes use atomic replacement. Unknown metadata is preserved when nodes or edges are updated.

## Node Contract

Graph nodes include:

- `node_id`
- `node_type`
- `label`
- `created_utc`
- `updated_utc`
- `source`
- `metadata`

Allowed node types:

- `repository`
- `mission`
- `task`
- `agent`
- `tool`
- `approval`
- `consensus`
- `artifact`
- `incident`
- `decision`
- `policy`
- `model`

## Edge Contract

Graph edges include:

- `edge_id`
- `from_node_id`
- `to_node_id`
- `edge_type`
- `created_utc`
- `source`
- `metadata`

Allowed edge types:

- `contains`
- `assigned_to`
- `reviewed_by`
- `approved_by`
- `rejected_by`
- `uses_tool`
- `targets_repository`
- `produced_artifact`
- `caused_incident`
- `resolved_by`
- `depends_on`
- `relates_to`
- `governed_by`
- `generated_from`
- `remembered_as`

## Mission Ingestion

Mission ingestion can write these facts:

- mission contains task
- task targets_repository repository
- task assigned_to primary agent
- task reviewed_by twin agent
- task uses_tool tool
- mission contains approval
- mission contains consensus
- approval approved_by or rejected_by actor when applicable
- consensus reviewed_by actor or agent
- mission remembered_as decision or incident for completion/failure metadata

Ingestion is explicit helper behavior. Creating or enqueueing a mission does not automatically write graph memory.

## Query Helpers

Phase 4 includes simple in-memory query helpers:

- find one node
- list nodes by type
- list neighbors
- find missions targeting a repository
- find tasks assigned to or reviewed by an agent
- return a mission subgraph

These helpers are intentionally small and local. They are not a retrieval replacement.
