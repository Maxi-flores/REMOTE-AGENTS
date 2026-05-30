# Sentient UI Adapter MVP

Phase 9 adds a compatibility-safe Sentient Control UI adapter layer that reads `.control_plane` snapshots and produces typed frontend-ready view models.

## Purpose

The adapter translates control-plane snapshots into panel-oriented view models for future Sentient-Control-UI rendering:

- runtime panel
- mission panel
- agent panel
- repository panel
- tool panel
- scheduler panel
- memory panel
- approval panel
- consensus panel
- observability panel

## Compatibility Boundary

Phase 9 does not:

- replace `platform_engine.py`
- replace `.platform_queue/next_task.json`
- add a web server
- add a daemon
- introduce distributed workers
- introduce cloud execution
- mutate runtime source state

It reads `.control_plane` snapshots only and writes optional UI artifacts under `.sentient_ui/`.

## Snapshot Reader

Reader helpers:

- `read_latest_snapshot(...)`
- `read_snapshot_history(...)`
- `safe_snapshot_summary(...)`

Behavior:

- read-only
- missing files return empty defaults
- malformed JSONL lines are skipped

## Trend Aggregation

Trend helpers:

- `build_metric_series(...)`
- `compute_delta(...)`
- `compute_status_trend(...)`
- `summarize_recent_alerts(...)`

These helpers operate on snapshot history only.

## View Model Envelope

`ViewModelEnvelope` includes:

- `view_model_id`
- `generated_utc`
- `source_snapshot_id`
- `schema_version`
- all panel payloads
- `alerts`
- `metadata`

Each panel is a `PanelViewModel` with status, summary, metrics, cards, tables, timelines, graph nodes/edges, alerts, and metadata.

## Exporter and CLI

Exporter helpers:

- `build_and_export_view_model(...)`
- `export_view_model_jsonl(...)`

CLI:

```bash
python src/sentient_ui/cli.py --print
python src/sentient_ui/cli.py --export
python src/sentient_ui/cli.py --export-jsonl
```

Write targets:

- `.sentient_ui/view_model.json` (atomic replace)
- `.sentient_ui/view_models.jsonl` (append-only)

No writes are made outside `.sentient_ui/`.

## Future Integration

Future Sentient-Control-UI phases can consume these view models directly as UI seed data, then later transition to API or streaming delivery when runtime contracts permit.

## Schema Versioning Note

Phase 10 adds schema manifests and compatibility checks for `.sentient_ui` artifacts. Existing view-model files are not rewritten in Phase 10. Migration planning is dry-run only and report output is limited to `.schema_migrations/`.

## Release Readiness Note

Phase 11 adds read-only drift analysis and release-readiness reports for `.sentient_ui` artifacts without rewriting view-model files.
