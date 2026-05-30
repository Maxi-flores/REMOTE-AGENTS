# Mission Engine MVP

Phase 2 introduces a Mission Engine MVP as a compatibility-safe control-plane layer above the existing local queue runtime.

## What It Is

The Mission Engine MVP creates durable mission and task state under `.missions/`.

It can:
- create a mission
- plan one task per target repository
- assign primary/twin agent classes through the existing repository governance router
- store mission JSON files atomically
- append telemetry events
- append approval records
- append consensus records
- adapt a pending mission task into the existing `.platform_queue/next_task.json` payload shape

## What It Is Not

The Mission Engine MVP does not:
- replace `.platform_queue/next_task.json`
- change `platform_engine.py`
- replace `.logs/semantic_memory.json`
- introduce distributed scheduling
- introduce cloud execution
- add a Human Approval API
- enforce human approval gates
- create a background daemon
- require canonical Phase 1 registries at runtime

Distributed scheduling remains a future Phase 6 concern.

Approval enforcement remains a future approval service concern. The existing twin review inside `platform_engine.py` remains the runtime gate for writes and isolated execution.

## Mission Contract

Mission fields:
- `mission_id`
- `title`
- `instruction`
- `target_repository`
- `target_repositories`
- `priority`
- `status`
- `risk_tier`
- `created_utc`
- `updated_utc`
- `tasks`
- `approvals`
- `consensus_records`
- `telemetry_events`
- `artifacts`
- `failure_reason`

Mission statuses:
- `draft`
- `planned`
- `awaiting_approval`
- `scheduled`
- `running`
- `validating`
- `completed`
- `failed`
- `cancelled`
- `archived`

## Task Contract

Task fields:
- `task_id`
- `mission_id`
- `instruction`
- `target_repository`
- `assigned_primary_agent`
- `assigned_twin_agent`
- `required_tools`
- `status`
- `priority`
- `depends_on`
- `created_utc`
- `updated_utc`
- `queue_payload`

Task statuses:
- `pending`
- `queued`
- `running`
- `blocked`
- `completed`
- `failed`
- `skipped`

## Storage

Mission files are written to `.missions/<mission_id>.json`.

Archived missions move to `.missions/archived/`.

The store uses JSON files and atomic replacement writes. It does not use a database or distributed lock system.

## Planning

The Phase 2 planner is intentionally simple:
- single-repository mission: one task
- multi-repository mission: one task per target repository
- missing repository: one default diagnostic task

Agent assignment uses `src/routers/repo_governance_router.py`, which still reads `config/agent_registry.json`.

## Queue Adapter

The queue adapter converts a mission task into the legacy queue payload:

```json
{
  "task_id": "...",
  "mission_id": "...",
  "instruction": "...",
  "priority": 0,
  "target_repository": "...",
  "source": "mission-engine",
  "enqueued_utc": "..."
}
```

The adapter uses exclusive file creation. If `.platform_queue/next_task.json` already exists, it returns a blocked result and does not overwrite the file.

## CLI Usage

Single repository:

```bash
python src/mission_engine/cli.py --repo "ConceptSHOP" --title "Fix Vite proxy" --instruction "Update Vite proxy config to point to new API port" --priority 2 --enqueue
```

Multiple repositories:

```bash
python src/mission_engine/cli.py --repos "Powerframe,PowerStarter" --title "Audit build scripts" --instruction "Audit build scripts and document missing commands" --priority 1 --enqueue
```

When `--enqueue` is supplied, only the first pending task is adapted into the legacy queue. Later scheduling remains future work.

## Approval and Consensus Records

Phase 3 adds durable recordkeeping for approvals and consensus outcomes. These records live inside mission JSON under `approvals` and `consensus_records`.

See `docs/approval-consensus.md` for the record contracts and the explicit non-enforcement boundary.

## Optional Memory Graph

Phase 4 adds optional mission ingestion into `.memory/graph.json`.

Mission creation, planning, and queue adaptation do not require graph ingestion. The graph is a seed memory structure for future planner, agent, and Sentient OS visualization work; it is not a retrieval replacement.

The existing `.logs/semantic_memory.json` behavior and `platform_engine.py` memory injection remain unchanged.

See `docs/semantic-memory-graph.md` for the graph contract and query helpers.
