# Release Gate Scenario Comparison MVP

Phase 13 adds advisory multi-policy release gate comparison for pre-release planning.

## Purpose

This phase provides read-only scenario comparison across multiple gate policies:

- scenario pack metadata under `config/release_gates/scenario_packs/`
- multi-policy simulation against one release-readiness report
- aggregate decision strategies for strict, permissive, and production candidate views
- optional scenario report exports under `.release_reports/`

## Compatibility Boundary

Phase 13 does not:

- replace `platform_engine.py`
- replace `.platform_queue/next_task.json`
- enforce release gates
- block mission execution
- mutate runtime source state

Scenario outputs are advisory-only.

## Scenario Packs

Built-in packs:

- `default_release_scenarios`
- `production_release_scenarios`
- `experimental_release_scenarios`

Supported comparison strategies:

- `compare_all`
- `strictest_wins`
- `permissive_preview`
- `production_candidate`

## Multi-Policy Simulation

Helpers:

- `simulate_scenario_pack(...)`
- `simulate_scenario_pack_from_report_file(...)`
- `aggregate_policy_decisions(...)`
- `explain_scenario_comparison(...)`

Each policy is loaded via the existing gate policy loader and evaluated via the existing advisory gate simulator.

## Scenario Reports

Helpers:

- `build_scenario_report(...)`
- `write_scenario_report(...)`
- `append_scenario_report_jsonl(...)`

Write targets:

- `.release_reports/scenario_comparison.json`
- `.release_reports/scenario_comparisons.jsonl`

Writes are restricted to `.release_reports/`.

## CLI

```bash
python src/release_gates/cli.py --list-scenarios
python src/release_gates/cli.py --scenario-pack default_release_scenarios --compare --print
python src/release_gates/cli.py --scenario-pack production_release_scenarios --compare --export
python src/release_gates/cli.py --scenario-pack experimental_release_scenarios --compare --export-jsonl
```

No server or daemon is introduced in this phase.

## Promotion Planning Note

Phase 14 adds advisory promotion planning that consumes scenario comparison outputs and generates staged `dev`/`staging`/`production` recommendations with rollback and CI handoff metadata.

## Release Center Note

Phase 15 adds advisory timeline synthesis that chains readiness, gates, scenarios, and promotion outputs into chronological Release Center narratives.
