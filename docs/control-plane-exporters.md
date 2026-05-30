# Control-Plane Exporters MVP

Phase 8 adds read-only control-plane snapshot/export helpers for future Sentient OS and Sentient-Control-UI consumption.

## Purpose

The exporters aggregate current local runtime metadata into snapshot artifacts that can seed future dashboards:

- runtime and queue status
- mission and task status summaries
- registry counts
- repository governance summaries
- scheduler worker and lease summaries
- tool routing summaries
- memory graph summaries
- approval and consensus summaries
- observability/error summaries

## Compatibility Boundary

Phase 8 does not:

- replace `platform_engine.py`
- replace `.platform_queue/next_task.json`
- add a web server
- add a daemon
- introduce distributed workers
- introduce cloud execution
- mutate missions, memory graph, scheduler state, governance records, queue files, or target repositories

It is read-only against source runtime state.

## Snapshot Contract

`ControlPlaneSnapshot` includes:

- `snapshot_id`
- `generated_utc`
- `schema_version`
- `runtime`
- `missions`
- `agents`
- `repositories`
- `tools`
- `scheduler`
- `memory_graph`
- `approvals`
- `consensus`
- `queue`
- `observability`
- `metadata`

Each section is a `DashboardSection` object with status, summary, metrics, records, warnings, errors, and metadata.

## Collectors

Phase 8 collectors read existing local state where available and handle missing files gracefully:

- `.platform_queue/next_task.json` and `.platform_queue/processing.lock`
- `.missions/`
- `config/registries/*` and legacy configs
- `.governance/repositories.json`
- `.scheduler/state.json`
- `.memory/graph.json`
- `.logs/consensus_metrics.json`
- `.logs/errors.json`

## Exporters

The snapshot builder and exporters:

- build one control-plane snapshot object
- write `snapshot.json` with atomic replacement
- append JSON lines to `snapshots.jsonl`
- write only under `.control_plane/`

Output paths:

- `.control_plane/snapshot.json`
- `.control_plane/snapshots.jsonl`

## CLI

```bash
python src/control_plane/cli.py --print
python src/control_plane/cli.py --export
python src/control_plane/cli.py --export-jsonl
```

No server process is started. The CLI is a one-shot read/export tool.

## Future Integration

Future Sentient OS UI phases can consume these snapshots as seed data for runtime, mission, tool, scheduler, memory, and governance views.

## Schema Versioning Note

Phase 10 adds schema manifests and compatibility checks for control-plane artifacts. It does not rewrite existing `.control_plane` files. Migration planning is dry-run only and report output is limited to `.schema_migrations/`.

## Release Readiness Note

Phase 11 adds read-only drift detection and release-readiness reports that inspect control-plane artifacts without rewriting them.
