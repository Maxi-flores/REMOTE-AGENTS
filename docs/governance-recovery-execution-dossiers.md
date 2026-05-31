# Governance Recovery Execution Dossier Layer (GREDL)

Phase 36 adds a deterministic, advisory-only handoff layer that converts Governance Recovery Plan actions into execution-ready dossiers for human review.

## Scope

- Input: `.control_plane/governance_recovery/latest.json`
- Output: `.control_plane/governance_recovery_dossiers/`
  - `latest.json`
  - `report_<timestamp>.json`
  - `history.jsonl`

## What It Produces

Each dossier contains:

- action and wave traceability
- objective and target component
- target artifact paths
- recommended manual commands
- validation commands
- review checklist
- rollback guidance
- Codex-ready advisory prompt
- execution risk classification

## Safety Boundary

GREDL is advisory only:

- no runtime execution
- no queue mutation
- no enforcement
- no repository mutation
- no `platform_engine.py` behavior changes

## CLI

```bash
python src/governance_recovery_dossiers/cli.py --print
python src/governance_recovery_dossiers/cli.py --export
python src/governance_recovery_dossiers/cli.py --export-jsonl
python src/governance_recovery_dossiers/cli.py --from-recovery-report ".control_plane/governance_recovery/latest.json" --print
```

## Optional Integrations

- Executive Briefing can include dossier availability and high-risk dossier counts.
- Strategic Missions can generate dossier-driven governance mission recommendations.

If dossier artifacts are missing, existing behavior remains unchanged.

