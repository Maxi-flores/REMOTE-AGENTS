# Portfolio Critical Path Intelligence (PCPI)

Phase 30 adds deterministic critical-path analysis to portfolio governance.

## Scope

PCPI consumes:

- dependency graph intelligence
- portfolio orchestration status
- onboarding recommendation priorities

and computes:

- repository influence score
- repository critical path score
- highest-leverage recommendation ordering

## Scoring

Deterministic scoring only (no model calls):

- Influence score: weighted consumer/provider/chain/risk/readiness factors.
- Critical path score: weighted influence + readiness deficit + downstream blast radius + severity + onboarding urgency.

## Outputs

PCPI writes only under:

- `.control_plane/portfolio_critical_path/latest.json`
- `.control_plane/portfolio_critical_path/report_<timestamp>.json`
- `.control_plane/portfolio_critical_path/history.jsonl`

## CLI

```bash
python src/portfolio_critical_path/cli.py --print
python src/portfolio_critical_path/cli.py --export
python src/portfolio_critical_path/cli.py --export-jsonl
```

## Compatibility Boundary

Phase 30 is advisory-only and does not:

- modify `platform_engine.py`
- modify `.platform_queue/next_task.json`
- modify external repositories
- execute tasks
- enforce runtime behavior

