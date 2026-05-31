# Handoff Package Refinement Engine (HPRE)

Phase 23 adds an advisory-only refinement layer over remediation handoff packages.

## Purpose

HPRE detects broad implementation handoff packages and deterministically splits them into smaller subsystem-scoped packages.

## Safety Boundary

This phase is advisory-only:
- no runtime execution changes
- no queue mutation
- no task enqueue
- no repository mutation
- no enforcement

Runtime remains unchanged:
- `src/orchastrator/platform_engine.py` behavior unchanged
- `.platform_queue/next_task.json` semantics unchanged

## Inputs

Default:
- `.control_plane/remediation_handoffs/latest.json`

Optional:
- `--from-handoff-report <path>`

## Outputs

Writes only under:
- `.control_plane/handoff_refinements/`

Artifacts:
- `latest.json`
- `report_<timestamp>.json`
- `history.jsonl`

## Refinement Rules

A package is treated as broad when one or more is true:
- more than 3 target files
- more than 1 inferred subsystem
- more than 2 validation commands
- mixed inferred change types

Split grouping is deterministic by:
1. subsystem
2. change type

## CLI

```bash
python src/handoff_refinement/cli.py --print
python src/handoff_refinement/cli.py --export
python src/handoff_refinement/cli.py --export-jsonl
python src/handoff_refinement/cli.py --from-handoff-report ".control_plane/remediation_handoffs/latest.json"
python src/handoff_refinement/cli.py --limit 5
```

## Optional Integrations

- Strategic missions can prefer refined packages when present.
- Executive briefing can report refinement coverage and remaining high-risk refined packages.

If no refinement report exists, existing behavior remains unchanged.
