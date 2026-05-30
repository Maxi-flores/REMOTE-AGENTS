# Release Gate Simulation MVP

Phase 12 adds advisory gate simulation and policy threshold profiles for pre-release guidance.

## Purpose

This phase simulates gate outcomes from release-readiness reports without enforcing runtime behavior:

- configurable gate policy profiles
- advisory gate decision simulation
- dry-run gate trace exports

## Compatibility Boundary

Phase 12 does not:

- replace `platform_engine.py`
- replace `.platform_queue/next_task.json`
- add a web server
- add a daemon
- enforce runtime gates
- block mission execution
- mutate runtime source state

Gate decisions are advisory-only in this phase.

## Policy Profiles

Policies are stored in `config/release_gates/`:

- `default_gate_policy.json`
- `strict_gate_policy.json`
- `experimental_gate_policy.json`

Each policy defines score thresholds, blocking toggles, warning/error limits, required artifact presence, and an `advisory_only` flag.

## Simulator

Simulation helpers:

- `simulate_gate(report, policy)`
- `simulate_gate_from_report_file(...)`
- `explain_gate_decision(...)`

The simulator evaluates:

- readiness score threshold
- critical findings
- malformed artifacts
- missing artifacts
- unsupported versions
- warning/error counts
- required artifact coverage

Output is a structured `GateDecision` object.

## Trace Writers

Trace helpers:

- `build_gate_trace(...)`
- `write_gate_trace(...)`
- `append_gate_trace_jsonl(...)`

Write targets:

- `.release_reports/gate_trace.json`
- `.release_reports/gate_traces.jsonl`

No writes are allowed outside `.release_reports/`.

## CLI

```bash
python src/release_gates/cli.py --list-policies
python src/release_gates/cli.py --policy default_gate_policy --print
python src/release_gates/cli.py --policy strict_gate_policy --export
python src/release_gates/cli.py --policy experimental_gate_policy --export-jsonl
```

No server or daemon is started.

## Future Promotion Path

Future phases may promote these advisory simulations into optional or mandatory CI/pre-release enforcement gates.

## Scenario Comparison Note

Phase 13 adds advisory multi-policy scenario packs and comparison reporting. This allows side-by-side evaluation of `default`, `strict`, and `experimental` policy outcomes without enforcing runtime behavior.

## Promotion Planning Note

Phase 14 adds advisory staged promotion profiles and recommendation planning. It does not deploy, enforce gates, run CI, or run git operations.

## Release Center Note

Phase 15 adds advisory timeline and milestone synthesis for release narratives. It remains read-only against source artifacts and writes only optional timeline artifacts under `.release_reports/`.
