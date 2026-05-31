# Governance Recovery Approval Readiness Layer (GRARL)

Phase 37 adds a deterministic advisory layer that evaluates governance recovery dossiers and classifies approval readiness.

## Scope

- Input: `.control_plane/governance_recovery_dossiers/latest.json`
- Output: `.control_plane/governance_approval_readiness/`
  - `latest.json`
  - `report_<timestamp>.json`
  - `history.jsonl`

## Approval Statuses

- `ready_for_review`
- `needs_review`
- `blocked`
- `rejected_advisory`
- `unknown`

## Readiness Rules

Ready for review requires:

- `advisory_only` is true
- no forbidden runtime/queue paths in `target_artifacts`
- non-empty validation commands
- non-empty rollback guidance
- non-empty review checklist
- non-empty codex prompt
- risk is `low` or `medium`

Blocked conditions include:

- forbidden path hits
- queue path hits
- missing validation commands
- advisory-only violations

Needs review includes:

- high/critical risk
- broad scope patterns

Rejected advisory includes:

- enforcement/auto-approval/auto-execution language

## CLI

```bash
python src/governance_approval_readiness/cli.py --print
python src/governance_approval_readiness/cli.py --export
python src/governance_approval_readiness/cli.py --export-jsonl
```

## Safety Boundary

GRARL is advisory-only:

- no task execution
- no approvals granted automatically
- no queue mutation
- no runtime behavior changes
- no repository mutation

