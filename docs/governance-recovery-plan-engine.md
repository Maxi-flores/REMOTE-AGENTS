# Governance Recovery Plan Engine (GRPE)

Phase 35 adds a deterministic recovery planner that converts the governance index into actionable advisory recovery waves.

## Scope

- Consumes latest governance index report.
- Identifies weak components and maps them into score-improvement actions.
- Estimates advisory score impact per action.
- Groups actions into execution waves with recommended sequence.
- Writes only under `.control_plane/governance_recovery/`.

## CLI

```bash
python src/governance_recovery/cli.py --print
python src/governance_recovery/cli.py --export
python src/governance_recovery/cli.py --export-jsonl
```

## Compatibility

- Advisory-only.
- No queue mutation.
- No runtime behavior replacement.
- No external repository mutation.

