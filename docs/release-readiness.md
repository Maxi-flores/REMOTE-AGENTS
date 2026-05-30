# Release Readiness Drift and Reporting MVP

Phase 11 adds read-only contract drift detection and release-readiness reporting for control-plane, Sentient UI, and schema manifest artifacts.

## Purpose

This phase provides advisory pre-release analysis without changing runtime behavior:

- manifest-vs-artifact drift findings
- JSON and JSONL artifact validation summaries
- readiness scoring and status classification
- release report exports for audit trails

## Compatibility Boundary

Phase 11 does not:

- replace `platform_engine.py`
- replace `.platform_queue/next_task.json`
- add a web server
- add a daemon
- introduce distributed workers
- introduce cloud execution
- rewrite `.control_plane` artifacts
- rewrite `.sentient_ui` artifacts
- rewrite schema manifests

Reports are advisory and do not enforce runtime gates yet.

## Drift Detection

Drift analyzer helpers:

- `compare_artifact_to_manifest(...)`
- `analyze_control_plane_snapshot(...)`
- `analyze_sentient_ui_view_model(...)`
- `analyze_control_plane_jsonl(...)`
- `analyze_sentient_ui_jsonl(...)`
- `analyze_schema_manifest(...)`

Supported drift finding types include missing required fields, unsupported/deprecated versions, malformed/missing artifacts, JSONL invalid lines, and compatibility warnings.

## Readiness Scoring

Scoring behavior:

- start at 100
- warning: -5
- error: -20
- critical: -50 and blocker
- malformed artifact, missing required artifact, unsupported version => blocker
- deprecated version => warning

Status classification:

- `ready`: score >= 90 and no blockers
- `ready_with_warnings`: score >= 70 and no blockers
- `blocked`: blockers present or score < 70
- `unknown`: no checked artifacts and no findings

## Report Writer

Helpers:

- `build_full_release_readiness_report()`
- `write_release_readiness_report(...)`
- `append_release_readiness_report_jsonl(...)`

Write targets:

- `.release_reports/release_readiness.json` (atomic)
- `.release_reports/release_readiness.jsonl` (append-only)

No writes are allowed outside `.release_reports/`.

## CLI

```bash
python src/release_readiness/cli.py --print
python src/release_readiness/cli.py --export
python src/release_readiness/cli.py --export-jsonl
python src/release_readiness/cli.py --check-file ".control_plane/snapshot.json" --artifact-type control_plane_snapshot
```

The CLI prints JSON to stdout and stays read-only unless export flags are provided.

## Future Use

Future phases may promote these advisory reports into pre-release gates for Sentient OS rollout workflows.

## Gate Simulation Note

Phase 12 adds advisory gate simulation policies and decision traces that consume release-readiness reports. These simulated gates do not enforce runtime behavior yet.

## Scenario Comparison Note

Phase 13 adds advisory scenario packs that run multiple gate policies against the same readiness report and produce comparison summaries for release planning.

## Promotion Planning Note

Phase 14 adds advisory promotion recommendations that consume scenario comparison reports and emit staged release guidance for `dev`, `staging`, and `production`.

## Release Center Note

Phase 15 synthesizes advisory release timeline events and milestones from readiness, gate, scenario, and promotion artifacts for future Sentient OS Release Center views.
