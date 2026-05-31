# Portfolio Dependency Intelligence Layer (PDIL)

Phase 29 adds deterministic dependency-aware portfolio intelligence.

## Scope

PDIL models repository dependencies and analyzes:

- providers and consumers
- dependency chains
- dependency blockers
- dependency risk propagation
- unknown dependencies

## Inputs

- `.config/portfolio/portfolio_registry.json`
- `.config/portfolio/dependencies.json`
- `.control_plane/portfolio_bootstrap/latest.json` (optional)
- `.control_plane/portfolio_onboarding_recommendations/latest.json` (optional)
- `.control_plane/portfolio/latest.json` (optional)

## Outputs

PDIL writes only under:

- `.control_plane/portfolio_dependencies/latest.json`
- `.control_plane/portfolio_dependencies/report_<timestamp>.json`
- `.control_plane/portfolio_dependencies/history.jsonl`

## CLI

```bash
python src/portfolio_dependencies/cli.py --print
python src/portfolio_dependencies/cli.py --export
python src/portfolio_dependencies/cli.py --export-jsonl
```

## Compatibility Boundary

Phase 29 is advisory-only and does not:

- modify `platform_engine.py`
- modify `.platform_queue/next_task.json`
- modify external repositories
- execute tasks
- enforce runtime behavior

