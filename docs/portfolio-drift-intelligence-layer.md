# Portfolio Drift Intelligence Layer (PDIL-2)

Phase 33 adds deterministic drift detection across portfolio artifacts.

## Scope

- Compares portfolio registry, dependency registry, bootstrap, onboarding, dependency findings, critical-path recommendations, roadmap, progress, and portfolio reports.
- Detects missing references, stale artifacts, contradictory status/readiness signals, and orphaned planning references.
- Emits advisory findings only.
- Writes outputs only under `.control_plane/portfolio_drift/`.

## CLI

```bash
python src/portfolio_drift/cli.py --print
python src/portfolio_drift/cli.py --export
python src/portfolio_drift/cli.py --export-jsonl
```

## Compatibility

- Advisory-only.
- No runtime execution changes.
- No queue mutation.
- No external repository mutation.

