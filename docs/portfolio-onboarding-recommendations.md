# Portfolio Onboarding Recommendations (PROR)

Phase 28 converts portfolio bootstrap onboarding gaps into repository-specific advisory recommendation packages.

## Scope

PROR consumes the latest portfolio bootstrap report and generates deterministic recommendations for each repository:

- `registered` and not discovered (path/registration guidance)
- discovered with `none` artifacts (baseline advisory artifact guidance)
- discovered with `partial` artifacts (missing-layer completion guidance)
- discovered with `complete` artifacts (periodic refresh guidance)

## Outputs

PROR writes artifacts only under:

- `.control_plane/portfolio_onboarding_recommendations/latest.json`
- `.control_plane/portfolio_onboarding_recommendations/report_<timestamp>.json`
- `.control_plane/portfolio_onboarding_recommendations/history.jsonl`

## CLI

```bash
python src/portfolio_onboarding_recommendations/cli.py --print
python src/portfolio_onboarding_recommendations/cli.py --export
python src/portfolio_onboarding_recommendations/cli.py --export-jsonl
python src/portfolio_onboarding_recommendations/cli.py --from-bootstrap-report ".control_plane/portfolio_bootstrap/latest.json"
```

## Compatibility Boundary

Phase 28 is advisory-only and does not:

- modify `platform_engine.py`
- modify `.platform_queue/next_task.json`
- modify external repositories
- execute tasks or packages
- enforce runtime behavior

