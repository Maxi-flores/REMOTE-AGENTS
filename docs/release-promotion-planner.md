# Release Promotion Planner MVP

Phase 14 adds advisory staged promotion planning for `dev`, `staging`, and `production`.

## Purpose

This phase consumes scenario comparison outputs and produces promotion recommendations with:

- environment-specific promotion profiles
- advisory recommendation decisions
- rollback precheck metadata
- CI handoff metadata
- optional promotion report artifacts

## Compatibility Boundary

Phase 14 does not:

- replace `platform_engine.py`
- replace `.platform_queue/next_task.json`
- enforce release gates
- deploy anything
- run CI
- run git commands
- mutate runtime source state

All outputs are advisory-only.

## Promotion Profiles

Profiles are stored in `config/release_gates/promotion_profiles/`:

- `dev_promotion_profile.json`
- `staging_promotion_profile.json`
- `production_promotion_profile.json`

Each profile defines thresholds and requirements for:

- scenario pack expectation
- aggregate status/decision acceptance
- blocker tolerance
- rollback planning
- CI handoff metadata

## Planner and Metadata Builders

Helpers:

- `plan_promotion(...)`
- `plan_promotion_from_scenario_report(...)`
- `explain_promotion_recommendation(...)`
- `build_rollback_precheck(...)`
- `build_ci_handoff_artifact(...)`

Recommendation outcomes:

- `promote`
- `promote_with_warnings`
- `hold`
- `blocked`
- `unknown`

## Promotion Reports

Helpers:

- `build_promotion_report(...)`
- `write_promotion_report(...)`
- `append_promotion_report_jsonl(...)`

Write targets:

- `.release_reports/promotion_recommendations.json`
- `.release_reports/promotion_recommendations.jsonl`

Writes are restricted to `.release_reports/`.

## CLI

```bash
python src/release_gates/cli.py --list-promotion-profiles
python src/release_gates/cli.py --profile dev_promotion_profile --plan-promotion --print
python src/release_gates/cli.py --profile staging_promotion_profile --plan-promotion --export
python src/release_gates/cli.py --profile production_promotion_profile --plan-promotion --export-jsonl
python src/release_gates/cli.py --plan-all-promotions --print
```

No server or daemon is introduced.

## Release Center Timeline Note

Phase 15 adds advisory timeline and milestone synthesis that consumes promotion, scenario, gate, and readiness artifacts to build a release narrative for future Release Center views.
