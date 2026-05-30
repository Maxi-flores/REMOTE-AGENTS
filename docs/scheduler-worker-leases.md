# Scheduler Worker Leases MVP

Phase 6 adds local scheduling metadata, worker descriptors, and task lease records.

## Purpose

This phase prepares REMOTE-AGENTS and Sentient OS to visualize workers, leases, and queue backpressure before real distributed scheduling exists.

It is planning metadata only.

## Compatibility Boundary

Phase 6 does not:

- replace `.platform_queue/next_task.json`
- replace `platform_engine.py`
- introduce real distributed workers
- introduce cloud execution
- add a network service
- add a daemon
- require scheduler metadata at runtime
- execute tasks
- mutate the legacy queue

The current queue remains `.platform_queue/next_task.json`.

Real distributed scheduling remains a future phase.

## Worker Descriptor Contract

Worker descriptors include:

- `worker_id`
- `worker_type`
- `display_name`
- `status`
- `capabilities`
- `supported_providers`
- `supported_repository_groups`
- `max_concurrent_tasks`
- `hardware_budget`
- `created_utc`
- `updated_utc`
- `metadata`

Allowed worker types:

- `local_ollama`
- `local_codex`
- `local_claude_code`
- `local_mcp`
- `local_shell`
- `browser_runtime`
- `future_cloud`

Allowed worker statuses:

- `registered`
- `idle`
- `busy`
- `degraded`
- `offline`
- `disabled`

## Task Lease Contract

Task leases include:

- `lease_id`
- `task_id`
- `mission_id`
- `worker_id`
- `lease_status`
- `priority`
- `acquired_utc`
- `expires_utc`
- `renewed_utc`
- `released_utc`
- `metadata`

Allowed lease statuses:

- `active`
- `renewed`
- `released`
- `expired`
- `failed`
- `cancelled`

## Local State Store

Scheduler state is stored at:

```text
.scheduler/state.json
```

Shape:

```json
{
  "schema_version": 1,
  "workers": {},
  "leases": {},
  "scheduler_events": []
}
```

Writes use atomic replacement. The store is local JSON only and does not implement distributed locking.

## Planner Behavior

The planner can:

- choose a worker for a task
- estimate task risk
- return a schedule plan
- explain the schedule decision

Rules:

- prefer matching provider, capability, and repository group
- prefer idle workers over busy workers
- never schedule to offline or disabled workers
- return a blocked planning result when no worker matches
- never execute tasks
- never mutate `.platform_queue/next_task.json`

## Queue Compatibility Helpers

Phase 6 includes read-only helpers that describe the legacy queue contract, detect whether the single queue slot is occupied, and explain lock/backpressure state.

These helpers do not enqueue work. They exist so future Sentient OS views can explain why a local queue is available, occupied, or locked.
