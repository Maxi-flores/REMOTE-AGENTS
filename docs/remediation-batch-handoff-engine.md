# Remediation Batch Handoff Engine (RBHE)

Phase 22 adds an advisory-only handoff layer that converts remediation batches into deterministic implementation packages and Codex-ready prompts.

## Scope

RBHE is advisory only:
- no runtime execution
- no queue mutation
- no auto-enqueue
- no repository mutation
- no git operations
- no model invocation

Runtime remains unchanged:
- `src/orchastrator/platform_engine.py` is unchanged.
- `.platform_queue/next_task.json` semantics are unchanged.

## Input

Primary input:
- `.control_plane/remediation_plans/latest.json`

Fallback:
- `.control_plane/remediation_plans/remediation_plan_report.json`

Override:
- `--from-remediation-report <path>`

## Output

Writes only under:
- `.control_plane/remediation_handoffs/`

Artifacts:
- `latest.json`
- `report_<timestamp>.json`
- `history.jsonl`

## CLI

```bash
python src/remediation_handoff/cli.py --print
python src/remediation_handoff/cli.py --export
python src/remediation_handoff/cli.py --export-jsonl
python src/remediation_handoff/cli.py --limit 3 --print
```

## Generated Package Contents

Each package includes:
- objective
- target files
- expected changes (additions/updates/notes)
- validation commands
- risks
- human review notes
- codex prompt text for manual operator use

RBHE never executes these packages automatically.
