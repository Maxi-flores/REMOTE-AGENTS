# Portfolio Governance Health Index (PGHI)

Phase 34 adds a deterministic portfolio governance scorecard synthesizing multiple advisory portfolio reports into a single health index.

## Scope

- Consumes latest artifacts from:
  - portfolio orchestration
  - bootstrap
  - onboarding recommendations
  - dependency intelligence
  - critical-path intelligence
  - roadmap
  - progress
  - drift
- Produces:
  - governance score
  - governance status
  - component scores
  - top reasons
  - top recommendations

## Output location

- `.control_plane/portfolio_governance_index/latest.json`
- `.control_plane/portfolio_governance_index/report_<timestamp>.json`
- `.control_plane/portfolio_governance_index/history.jsonl`

## CLI

```bash
python src/portfolio_governance_index/cli.py --print
python src/portfolio_governance_index/cli.py --export
python src/portfolio_governance_index/cli.py --export-jsonl
```

## Compatibility

- Advisory-only.
- No runtime execution changes.
- No queue mutation.
- No external repository mutation.

