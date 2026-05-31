# Portfolio Strategic Execution Roadmap Layer (PSERL)

Phase 31 adds an advisory-only portfolio roadmap planner that converts Portfolio Critical Path Intelligence into deterministic execution waves.

## Scope

- Consumes advisory artifacts only:
  - `.control_plane/portfolio_critical_path/latest.json`
  - `.control_plane/portfolio/latest.json`
  - `.control_plane/portfolio_dependencies/latest.json`
  - `.control_plane/portfolio_onboarding_recommendations/latest.json`
- Produces advisory roadmap artifacts only:
  - `.control_plane/portfolio_roadmap/latest.json`
  - `.control_plane/portfolio_roadmap/report_<timestamp>.json`
  - `.control_plane/portfolio_roadmap/history.jsonl`

## Roadmap horizons

- `near_term`: P0/P1 critical-path actions, onboarding blockers, high dependency risk.
- `mid_term`: P2 actions, portfolio readiness and intelligence expansion.
- `long_term`: P3/P4 ecosystem hardening and federation preparation.

## Execution waves

- `wave_1`: near-term critical unblockers.
- `wave_2`: mid-term readiness expansion.
- `wave_3`: long-term hardening and maturity.

Wave sequencing is dependency-aware and deterministic.

## CLI

```bash
python src/portfolio_roadmap/cli.py --print
python src/portfolio_roadmap/cli.py --export
python src/portfolio_roadmap/cli.py --export-jsonl
```

## Compatibility guarantees

- Advisory-only.
- No task execution.
- No queue mutation.
- No runtime path replacement.
- `platform_engine.py` and `.platform_queue/next_task.json` behavior remain unchanged.

