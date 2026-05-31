# Portfolio Artifact Bootstrap Layer (PABL)

Phase 27 adds deterministic repository onboarding and advisory artifact discovery across the portfolio registry.

## Scope

PABL discovers portfolio repositories, inspects repository roots, and produces onboarding/readiness records without modifying those repositories.

## What PABL Checks

Repository structure presence:

- `README.md`
- `docs/`
- `src/`
- `tests/`

Advisory artifact presence:

- `.control_plane/`
- `.control_plane/repository_intelligence/`
- `.control_plane/work_queue/`
- `.control_plane/execution_dossiers/`

## Readiness Estimation

Readiness is deterministic and documented in each record metadata:

- `README.md`: 15
- `docs/`: 15
- `src/`: 25
- `tests/`: 20
- advisory artifacts: up to 25 (proportional coverage across intelligence/work_queue/execution_dossiers)

Score is bounded to `0..100`.

## Outputs

PABL writes only inside REMOTE-AGENTS:

- `.control_plane/portfolio_bootstrap/latest.json`
- `.control_plane/portfolio_bootstrap/report_<timestamp>.json`
- `.control_plane/portfolio_bootstrap/history.jsonl`

PABL never writes into external repositories.

## CLI

```bash
python src/portfolio_bootstrap/cli.py --print
python src/portfolio_bootstrap/cli.py --export
python src/portfolio_bootstrap/cli.py --export-jsonl
```

## Compatibility Boundary

Phase 27 does not:

- modify `platform_engine.py`
- modify `.platform_queue/next_task.json`
- execute tasks or dossiers
- modify external repositories
- add enforcement

