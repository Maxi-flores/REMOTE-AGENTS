# Repository Remediation Planner (RRP)

Phase 21 adds an advisory-only Repository Remediation Planner that transforms Repository Intelligence findings into deterministic remediation plans.

## Scope

RRP is planning-only:
- no runtime execution
- no mission enqueue
- no queue mutation
- no repository mutation
- no enforcement

Runtime remains unchanged:
- `src/orchastrator/platform_engine.py` remains the live execution path.
- `.platform_queue/next_task.json` semantics remain unchanged.

## Inputs

RRP reads repository intelligence from:
- `.control_plane/repository_intelligence/latest.json` when available
- fallback: `.control_plane/repository_intelligence/repository_intelligence_report.json`
- optional override: CLI `--from-rie-report <path>`

## Outputs

RRP writes only under `.control_plane/remediation_plans/`:
- `remediation_plan_report.json` (latest)
- `remediation_plan_report_<timestamp>.json` (timestamped)
- `remediation_plan_reports.jsonl` (history, append-only)

## Contracts

RRP defines:
- `RemediationItem`
- `RemediationBatch`
- `RemediationPlanReport`

All outputs include `advisory_only: true`.

## CLI

```bash
python src/remediation_planner/cli.py --print
python src/remediation_planner/cli.py --export
python src/remediation_planner/cli.py --export-jsonl
python src/remediation_planner/cli.py --from-rie-report ".control_plane/repository_intelligence/repository_intelligence_report.json" --limit 10 --print
```

## Optional Integrations

- Strategic Missions: top remediation batches can be converted into advisory mission candidates.
- Executive Briefing: high-priority remediation backlog can be surfaced as repository risk.

If remediation artifacts are absent, existing behavior is unchanged.
