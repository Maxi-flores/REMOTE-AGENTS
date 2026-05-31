# Portfolio Orchestration Layer (POL)

Phase 26 adds a deterministic, advisory-only portfolio orchestration layer for multi-repository planning.

## Scope

POL aggregates repository-level advisory artifacts into a portfolio report:

- repository intelligence posture
- remediation backlog posture
- work queue posture
- execution dossier posture
- deterministic health and readiness scoring
- portfolio findings and recommended execution order

## Inputs

POL reads local advisory artifacts when available:

- `.control_plane/repository_intelligence/repository_intelligence_report.json`
- `.control_plane/remediation_plans/remediation_plan_report.json`
- `.control_plane/work_queue/latest.json`
- `.control_plane/execution_dossiers/latest.json`
- portfolio repository registry (`.config/portfolio/portfolio_registry.json` by default)

Missing inputs are tolerated. Repository status falls back to `unknown`/low-score semantics instead of failing.

## Outputs

POL writes optional artifacts under `.control_plane/portfolio/`:

- `latest.json`
- `report_<timestamp>.json`
- `history.jsonl`

## CLI

```bash
python src/portfolio_orchestration/cli.py --print
python src/portfolio_orchestration/cli.py --export
python src/portfolio_orchestration/cli.py --export-jsonl
python src/portfolio_orchestration/cli.py --registry ".config/portfolio/portfolio_registry.json"
```

## Compatibility Boundary

Phase 26 does not:

- modify `src/orchastrator/platform_engine.py`
- modify `src/orchestrator/platform_engine.py` runtime behavior
- mutate `.platform_queue/next_task.json`
- execute tasks or dossiers
- enforce runtime gates
- modify target repositories

