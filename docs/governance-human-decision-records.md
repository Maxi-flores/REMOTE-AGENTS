# Governance Human Decision Record Layer (GHDRL)

Phase 39 adds durable, advisory-only human decision recordkeeping for governance approval packets.

## Scope

- Inputs:
  - `.control_plane/governance_approval_packets/latest.json`
- Outputs:
  - `.control_plane/governance_decisions/decisions.json`
  - `.control_plane/governance_decisions/latest.json`
  - `.control_plane/governance_decisions/report_<timestamp>.json`
  - `.control_plane/governance_decisions/history.jsonl`

## Decision Types

- `approve_for_manual_execution`
- `request_changes`
- `reject`
- `defer`

## Safety Rules

Decision records are advisory metadata only:

- no execution
- no enqueue
- no runtime behavior change
- no queue mutation

For `approve_for_manual_execution`, the record must include:

- `runtime_paths_reviewed`
- `queue_mutation_forbidden_acknowledged`
- `validation_commands_reviewed`
- `rollback_guidance_reviewed`
- `manual_execution_only_acknowledged`

## CLI

```bash
python src/governance_decisions/cli.py --print

python src/governance_decisions/cli.py --record-decision \
  --packet-id <packet_id> \
  --decision defer \
  --reviewer "Max" \
  --notes "Defer until portfolio paths are reviewed."

python src/governance_decisions/cli.py --export --export-jsonl
```

## Integration

Optional read-only integration:

- Executive briefing can summarize pending/approved/request-changes/rejected/deferred states.
- Strategic missions can prioritize packet review and change-resolution follow-up.

