# Schema Versioning and Migration Dry-Run MVP

Phase 10 adds schema manifests, compatibility checks, migration planners, and CLI tooling for `.control_plane` and `.sentient_ui` artifacts.

## Purpose

This phase provides safe contract-evolution primitives for Sentient OS data artifacts:

- schema manifests
- artifact compatibility checks
- JSONL compatibility summaries
- migration planning stubs
- dry-run migration reports

## Compatibility Boundary

Phase 10 does not:

- replace `platform_engine.py`
- replace `.platform_queue/next_task.json`
- add a web server
- add a daemon
- mutate runtime source state
- perform destructive migration
- rewrite `.control_plane` or `.sentient_ui` artifacts

Dry-run reports may be written only under `.schema_migrations/`.

## Manifests

Manifest files:

- `config/schema_manifests/control_plane_snapshot.v1.json`
- `config/schema_manifests/sentient_ui_view_model.v1.json`

Each manifest defines artifact type, current/supported versions, required fields, optional fields, and compatibility notes.

## Checker

Checker helpers:

- `load_schema_manifest(...)`
- `detect_artifact_version(...)`
- `check_control_plane_snapshot_compatibility(...)`
- `check_sentient_ui_view_model_compatibility(...)`
- `check_artifact_file(...)`
- `check_jsonl_artifact_file(...)`

Behavior:

- read-only
- missing files return incompatible results with issues
- malformed JSON and JSONL are tolerated and reported
- JSONL checks validate each line and summarize failures

## Migration Planner

Planner helpers:

- `plan_control_plane_snapshot_migration(...)`
- `plan_sentient_ui_view_model_migration(...)`
- `plan_artifact_file_migration(...)`
- `write_migration_dry_run_report(...)`

Behavior:

- no destructive migration
- no in-place rewrite
- returns `not_required` when target version already matches
- returns `blocked`/`unsupported` for unknown versions
- dry-run reports write only under `.schema_migrations/`

## CLI

```bash
python src/schema_versioning/cli.py --check-control-plane
python src/schema_versioning/cli.py --check-sentient-ui
python src/schema_versioning/cli.py --check-file ".control_plane/snapshot.json" --artifact-type control_plane_snapshot
python src/schema_versioning/cli.py --plan-migration ".sentient_ui/view_model.json" --artifact-type sentient_ui_view_model --dry-run
```

The CLI prints JSON to stdout. It writes only when `--dry-run` is provided, and then only under `.schema_migrations/`.

## Future Evolution

Future phases may use these versioning and dry-run planning primitives to safely evolve Sentient OS data contracts before enabling managed migrations.

## Release Readiness Note

Phase 11 adds read-only contract drift analysis and readiness scoring that consume schema checker outputs. These reports remain advisory and do not enforce runtime gates yet.
