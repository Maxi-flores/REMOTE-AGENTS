# Governance Approval Packet Layer (GAPL)

Phase 38 adds deterministic advisory approval packet generation for governance recovery dossiers.

## Scope

- Inputs:
  - `.control_plane/governance_approval_readiness/latest.json`
  - `.control_plane/governance_recovery_dossiers/latest.json`
- Outputs:
  - `.control_plane/governance_approval_packets/latest.json`
  - `.control_plane/governance_approval_packets/report_<timestamp>.json`
  - `.control_plane/governance_approval_packets/history.jsonl`

## Packet Behavior

- Packets are generated for:
  - `ready_for_review`
  - `needs_review`
- Packets are not generated for:
  - `blocked`
  - `rejected_advisory`

Each packet includes:

- readiness context and risk summary
- dossier artifact scope
- validation commands
- rollback guidance
- blank human decision template

## Human Decision Template

Allowed decisions:

- `approve_for_manual_execution`
- `request_changes`
- `reject`
- `defer`

Template fields remain intentionally blank for reviewer completion.

## Safety Boundary

GAPL is advisory-only:

- no automatic approvals
- no automatic denials
- no execution
- no queue mutation
- no runtime behavior changes

