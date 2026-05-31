# Manual Execution Handoff Queue Layer (MEHQL)

Phase 40 adds a deterministic advisory manual execution handoff queue for governance operators.

## Scope

- Inputs:
  - `.control_plane/governance_decisions/latest.json`
  - `.control_plane/governance_approval_packets/latest.json`
- Outputs:
  - `.control_plane/manual_execution_queue/latest.json`
  - `.control_plane/manual_execution_queue/report_<timestamp>.json`
  - `.control_plane/manual_execution_queue/history.jsonl`

## Queue Status Mapping

- `approve_for_manual_execution` -> `approved_manual` (`P1`)
- `request_changes` -> `needs_changes` (`P2`)
- no decision -> `pending_review` (`P2`)
- `defer` -> `deferred` (`P3`)
- `reject` -> `rejected` (`P4`)

## Operator Guidance

Each queue item includes:

- packet/dossier linkage
- decision state
- operator next step
- validation command visibility
- safety notes

## Safety Boundary

MEHQL is advisory-only:

- no execution
- no queue mutation of `.platform_queue/next_task.json`
- no runtime approval
- no runtime behavior changes

