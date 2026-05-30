# Release Center Timeline MVP

Phase 15 adds advisory Release Center timeline and milestone synthesis.

## Purpose

This phase merges release artifacts into a chronological narrative:

- release readiness reports
- gate traces
- scenario comparisons
- promotion recommendations

It also synthesizes release milestones and escalation hints for future Sentient OS Release Center views.

## Compatibility Boundary

Phase 15 does not:

- enforce gates
- deploy
- run CI
- run git commands
- mutate runtime source state

Outputs are advisory-only.

## Timeline and Milestone Outputs

Release timeline report contains:

- timeline events
- derived milestones
- summary metrics
- escalation hints

Write targets:

- `.release_reports/release_timeline.json`
- `.release_reports/release_timeline.jsonl`

Writes are restricted to `.release_reports/`.

## CLI

```bash
python src/release_center/cli.py --print
python src/release_center/cli.py --export
python src/release_center/cli.py --export-jsonl
python src/release_center/cli.py --label "sentient-os-local-release" --export
```

No server or daemon is introduced in this phase.

