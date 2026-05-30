# Control Plane Orchestration Layer (Phase 17)

## Status

Phase 17 is complete as an advisory-only layer.

## Purpose

The Control Plane Orchestration Layer (CPOL) links existing advisory systems into a single, ordered planning flow without changing runtime execution:

1. mission
2. scheduler
3. tool_router
4. governance
5. memory_graph
6. release_readiness
7. release_gates
8. release_center
9. lifecycle
10. snapshot
11. sentient_ui

CPOL reads existing artifacts, reports stage status, and writes optional orchestration reports under `.control_plane/orchestration/`.

## Runtime Compatibility Boundary

CPOL does not:

- replace `platform_engine.py`
- replace `.platform_queue/next_task.json`
- enqueue or execute tasks
- enforce approvals, governance, or release gates
- mutate runtime state outside `.control_plane/orchestration/`

Legacy compatibility remains intact:

- `src/orchastrator/platform_engine.py` remains the runtime implementation path
- `src/orchestrator/platform_engine.py` remains the canonical compatibility alias

## Contracts

CPOL introduces:

- `ControlPlaneOrchestrationRequest`
- `ControlPlaneOrchestrationStageResult`
- `ControlPlaneOrchestrationReport`

All contracts require `advisory_only=true`.

## CLI

Examples:

```bash
python src/control_plane/orchestrator_cli.py --print
python src/control_plane/orchestrator_cli.py --export
python src/control_plane/orchestrator_cli.py --export-jsonl
python src/control_plane/orchestrator_cli.py --mission-id "mission_123" --trigger-source manual --print
```

Optional passthrough is available in `src/control_plane/cli.py`:

```bash
python src/control_plane/cli.py --run-orchestration --print
```

