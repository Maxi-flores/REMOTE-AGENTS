# Autonomous Work Queue Manager (AWQM)

Phase 24 adds an advisory-only work queue planner over refined implementation packages.

## Purpose

AWQM converts refined packages into deterministic queue items with:
- dependency awareness
- blocker tracking
- readiness scoring
- recommended execution order

## Safety Boundary

Advisory only:
- no runtime execution changes
- no queue mutation
- no task enqueue
- no repository mutation
- no enforcement

Runtime remains unchanged:
- `src/orchastrator/platform_engine.py` unchanged
- `.platform_queue/next_task.json` semantics unchanged

## Inputs

Default:
- `.control_plane/handoff_refinements/latest.json`

## Outputs

Writes only under:
- `.control_plane/work_queue/`

Artifacts:
- `latest.json`
- `report_<timestamp>.json`
- `history.jsonl`

## CLI

```bash
python src/work_queue_manager/cli.py --print
python src/work_queue_manager/cli.py --export
python src/work_queue_manager/cli.py --export-jsonl
python src/work_queue_manager/cli.py --limit 10
```

## Readiness and Dependencies

Dependencies are inferred deterministically from:
- subsystem
- change type
- package metadata

Readiness score is deterministic (0-100) from:
- risk
- dependency count
- blocker count
- effort
- subsystem concentration

Execution readiness states:
- `ready`
- `waiting`
- `blocked`
- `deferred`

## Optional Integrations

- Strategic Missions can ingest top queue items.
- Executive Briefing can report blocked/ready/deferred queue state.

If no work queue report exists, existing behavior remains unchanged.
