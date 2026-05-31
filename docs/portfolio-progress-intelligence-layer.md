# Portfolio Progress Intelligence Layer (PPIL)

Phase 32 adds deterministic trend tracking for portfolio advisory artifacts.

## Scope

- Reads advisory histories where available:
  - `.control_plane/portfolio/history.jsonl`
  - `.control_plane/portfolio_roadmap/history.jsonl`
  - `.control_plane/portfolio_bootstrap/history.jsonl`
  - `.control_plane/portfolio_dependencies/history.jsonl`
  - `.control_plane/portfolio_critical_path/history.jsonl`
- Computes current vs previous metrics and trend states.
- Produces advisory findings for declining or unknown trends.
- Writes only under `.control_plane/portfolio_progress/`.

## Trends

- Positive metrics: higher is improving.
- Negative metrics: lower is improving.
- Stable when `delta == 0`.
- Unknown when previous value is unavailable.

## CLI

```bash
python src/portfolio_progress/cli.py --print
python src/portfolio_progress/cli.py --export
python src/portfolio_progress/cli.py --export-jsonl
```

## Compatibility

- Advisory-only.
- No runtime execution changes.
- No `.platform_queue` mutation.
- No external repository mutation.

