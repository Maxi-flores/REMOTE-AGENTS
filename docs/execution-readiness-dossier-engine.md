# Execution Readiness Dossier Engine (ERDE)

Phase 25 adds an advisory-only execution dossier layer over work queue planning.

## Purpose

ERDE turns queue items into complete execution dossiers and codex execution packets with:
- target files
- expected changes
- validation plans
- review checklists
- rollback guidance
- traceability

## Safety Boundary

Advisory-only:
- no runtime execution
- no queue mutation
- no task enqueue
- no repository mutation
- no enforcement

Runtime remains unchanged:
- `src/orchastrator/platform_engine.py` unchanged
- `.platform_queue/next_task.json` semantics unchanged

## Inputs

Primary:
- `.control_plane/work_queue/latest.json`

Optional context:
- `.control_plane/handoff_refinements/latest.json`
- `.control_plane/remediation_handoffs/latest.json`

## Outputs

Writes only under:
- `.control_plane/execution_dossiers/`

Artifacts:
- `latest.json`
- `report_<timestamp>.json`
- `history.jsonl`

## CLI

```bash
python src/execution_dossier/cli.py --print
python src/execution_dossier/cli.py --export
python src/execution_dossier/cli.py --export-jsonl
python src/execution_dossier/cli.py --from-work-queue ".control_plane/work_queue/latest.json"
python src/execution_dossier/cli.py --limit 10
```

## Optional Integrations

- Executive briefing can summarize execution-ready dossier counts and high-risk dossier counts.
- Strategic missions can prioritize execution-ready dossiers.

If no dossier report exists, existing behavior remains unchanged.
