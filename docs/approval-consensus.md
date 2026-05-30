# Approval and Consensus Records

Phase 3 adds durable approval and consensus records to mission JSON state.

## Boundary

This phase is recordkeeping only.

It does not:
- replace twin approval in `platform_engine.py`
- enforce human approval gates
- change `.platform_queue/next_task.json`
- add a web server
- add distributed workers
- add cloud execution
- require external services

The existing twin review in `platform_engine.py` remains the actual runtime write/execute gate. Human approvals are now durable mission records, but they are not yet enforced by the scheduler/runtime. Enforcement belongs to a later approval service phase.

## Approval Records

Approval fields:
- `approval_id`
- `mission_id`
- `task_id`
- `action`
- `status`
- `requested_by`
- `reviewed_by`
- `reason`
- `risk_tier`
- `created_utc`
- `updated_utc`
- `expires_utc`
- `metadata`

Approval actions:
- `approve`
- `reject`
- `request_changes`
- `expire`

Approval statuses:
- `requested`
- `approved`
- `rejected`
- `changes_requested`
- `expired`
- `cancelled`

Helper functions:
- `create_approval_request`
- `approve_record`
- `reject_record`
- `request_changes_record`
- `expire_record`

## Consensus Records

Consensus fields:
- `consensus_id`
- `mission_id`
- `task_id`
- `consensus_type`
- `decision`
- `actor`
- `agent_class`
- `tool_name`
- `target_repository`
- `feedback`
- `created_utc`
- `metadata`

Consensus types:
- `twin`
- `quorum`
- `human`
- `policy`
- `system`

Consensus decisions:
- `approved`
- `rejected`
- `abstained`
- `changes_requested`
- `failed`

Helper function:
- `create_consensus_record`

## Store Support

`MissionStore` supports:
- `append_approval(mission_id, approval_record)`
- `append_consensus_record(mission_id, consensus_record)`

Both methods:
- read the mission
- validate the record
- append it to the mission JSON
- update `updated_utc`
- write atomically

Neither method enforces approval decisions.
