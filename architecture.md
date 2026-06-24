# REMOTE-AGENTS Architecture

## 1. Scope and Intent

REMOTE-AGENTS is a **local-first autonomous runtime** with a growing **advisory control-plane stack**.

Two architectural realities coexist:

- **Live runtime path (execution):** single-worker, queue-file driven, local model/tool loop.
- **Advisory control plane (analysis/planning):** deterministic artifact generators that read state and produce reports for governance, release, portfolio, and operator workflows.

The runtime is intentionally conservative: most newer layers are advisory and do **not** replace execution semantics.

## 2. Architectural Principles

- Local-first operation and compatibility with Ollama-style local models.
- Deterministic contracts for artifacts and reports.
- Advisory-first rollout: analysis and planning layers before enforcement.
- Runtime compatibility preservation (`.platform_queue/next_task.json` + `platform_engine.py`).
- Explicit policy/governance metadata and auditable outputs.
- File-system artifact contracts over always-on backend services.

## 3. High-Level Topology

```text
                    +-------------------------------+
                    |  Human / External Triggering  |
                    |  - dispatcher CLI             |
                    |  - gateway HTTP/WS            |
                    +---------------+---------------+
                                    |
                                    v
                    +-------------------------------+
                    | .platform_queue/next_task.json|
                    | .platform_queue/processing.lock|
                    +---------------+---------------+
                                    |
                                    v
                    +-------------------------------+
                    | Runtime Worker Engine          |
                    | src/orchastrator/platform_engine.py
                    | (alias: src/orchestrator/platform_engine.py)
                    +---------------+---------------+
                                    |
               +--------------------+---------------------+
               |                                          |
               v                                          v
    +-----------------------+                 +--------------------------+
    | Tool Execution Path   |                 | Runtime Logs / Failures  |
    | twin approval on      |                 | .logs/*, failed payloads |
    | side-effecting ops    |                 +-------------+------------+
    +-----------+-----------+                               |
                |                                           v
                v                            +-------------------------------+
 +------------------------------+            | Advisory Control-Plane Layers |
 | Registry / Repo Routing      |            | src/* + docs/* phase modules  |
 | config/agent_registry.json   |            | write to .control_plane/* and |
 +------------------------------+            | related advisory directories   |
                                             +-------------------------------+
```

## 4. Runtime Execution Plane (Authoritative)

### 4.1 Entrypoints

- `python src/orchastrator/platform_engine.py` (legacy, live implementation)
- `python src/orchestrator/platform_engine.py` (canonical compatibility alias)
- `python src/orchestrator/gateway.py` (ingestion API and telemetry)
- `python src/orchestrator/dispatcher.py` (manual enqueue + stale lock prune)

### 4.2 Core Runtime Contracts

- Single task file: `.platform_queue/next_task.json`
- Single-flight lock: `.platform_queue/processing.lock`
- Failed task archive: `.platform_queue/failed/`
- Error and consensus telemetry: `.logs/errors.json`, `.logs/consensus_metrics.json`
- Optional callback delivery outbox: `.platform_queue/outbound/*.json`

### 4.3 Runtime Data Flow

1. Task arrives via dispatcher CLI, gateway HTTP/WS, or direct file drop.
2. Worker acquires processing lock and reads the queued task.
3. Repository profile is resolved from `config/agent_registry.json` (fallback default profile exists).
4. Model/tool loop executes; side-effecting actions require twin approval.
5. On success, task file is removed; on failure, payload is archived and errors logged.
6. Optional completion envelope is retried through outbound callback dispatcher.

### 4.4 Runtime APIs

Gateway exposes:

- `POST /api/v1/trigger`
- `GET /health`
- `GET /ws/events`

`/health` includes queue, lock, memory, workspace, consensus, and semantic-memory signals.

## 5. Advisory Control Plane Architecture

The control plane is organized as phase-built modules under `src/`. They are predominantly read-only/advisory and emit deterministic artifacts.

### 5.1 Foundational Advisory Layers (Phases 1-17)

- Registries and governance metadata (`config/registries/*`, `src/repository_governance/`)
- Mission state + queue compatibility (`src/mission_engine/`)
- Semantic memory graph (`src/memory_graph/`)
- Tool routing policy layer (`src/tool_router/`)
- Scheduler metadata and lease planning (`src/scheduler/`)
- Snapshot exporters (`src/control_plane/`)
- Sentient UI adapter (`src/sentient_ui/`)
- Schema versioning and dry-run migration (`src/schema_versioning/`)
- Release readiness, gate simulation, promotion, and release-center synthesis (`src/release_readiness/`, `src/release_gates/`, `src/release_center/`)
- Lifecycle/capability matrix (`src/lifecycle_manager/`)
- CPOL orchestration (`src/control_plane/orchestrator.py`)

CPOL stage order:

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

### 5.2 Executive/Strategic Layers (Phases 18-25)

- Executive briefing synthesis (`src/executive_briefing/`)
- Strategic mission generation (`src/strategic_missions/`)
- Repository intelligence and remediation planning (`src/repository_intelligence/`, `src/remediation_planner/`)
- Remediation handoff refinement and queue/dossier generation:
  - `src/remediation_handoff/`
  - `src/handoff_refinement/`
  - `src/work_queue_manager/`
  - `src/execution_dossier/`

### 5.3 Portfolio/Governance Continuum (Phases 26-40)

- Portfolio orchestration and onboarding:
  - `src/portfolio_orchestration/`
  - `src/portfolio_bootstrap/`
  - `src/portfolio_onboarding_recommendations/`
- Dependency, critical-path, roadmap, progress, drift:
  - `src/portfolio_dependencies/`
  - `src/portfolio_critical_path/`
  - `src/portfolio_roadmap/`
  - `src/portfolio_progress/`
  - `src/portfolio_drift/`
- Governance index and recovery workflow:
  - `src/portfolio_governance_index/`
  - `src/governance_recovery/`
  - `src/governance_recovery_dossiers/`
  - `src/governance_approval_readiness/`
  - `src/governance_approval_packets/`
  - `src/governance_decisions/`
  - `src/manual_execution_queue/`

These layers produce operator-ready advisory packets and queues while preserving runtime behavior.

## 6. Storage and Artifact Topology

### 6.1 Runtime-Critical State

- `.platform_queue/` - execution queue, lock, failed/outbound payloads
- `.logs/` - runtime errors and consensus counters

### 6.2 Advisory State and Reports

- `.missions/` - mission/task state
- `.memory/` - semantic graph
- `.scheduler/` - worker/lease metadata
- `.governance/` - governance profile state
- `.control_plane/` - control-plane snapshots, orchestration outputs, executive/portfolio artifacts
- `.sentient_ui/` - UI view model exports
- `.schema_migrations/` - dry-run schema migration plans
- `.release_reports/` - release readiness/gate/promotion/timeline outputs
- `.lifecycle/` - capability/lifecycle state

### 6.3 Config and Contracts

- `config/agent_registry.json` - active runtime repository routing
- `config/platform_mcp_tools.json` - runtime tool schema
- `config/registries/*` - canonical advisory registries
- `config/release_gates/*` - gate/scenario/promotion profiles
- `config/schema_manifests/*` - schema version manifests
- `schema/*.json` - JSON schemas for cross-agent/runtime contracts

## 7. Security and Governance Model

- Repository-scoped routing and execution constraints per profile.
- Twin-agent approval for side-effecting tools.
- Default diagnostic fallback for unknown repositories.
- Advisory policy metadata for release, governance, and lifecycle domains.
- Separation of concern between execution and advisory planning to reduce accidental enforcement.

## 8. Frontend and Visualization Surfaces

- Terminal dashboard (`src/ui/terminal_dashboard.py`) for local operator visibility.
- Dashboard web workspace (`packages/dashboard-3d/`) for 3D telemetry/control visualization.
- Sentient UI adapter exports typed frontend-ready panel view models from control-plane snapshots.

## 9. Testing Strategy

- Extensive Python contract/integration tests under `tests/` covering runtime compatibility, advisory modules, report contracts, and no-queue-mutation guarantees.
- JavaScript workspace has dedicated lint/build scripts for the dashboard package.

## 10. Known Boundaries and Non-Goals (Current)

- No distributed queue guarantees.
- No cloud execution layer.
- No mandatory Human Approval API enforcement in runtime.
- No automatic deployment enforcement from release/governance layers.
- Advisory layers remain additive and mostly read-only with artifact writes in designated directories.

## 11. Practical Navigation Guide

If you are operating the system:

1. Start with `README.md` for runtime commands and phase overview.
2. Use `docs/runtime-contracts.md` for execution invariants.
3. Use `docs/architecture-roadmap.md` for phase-by-phase architecture evolution.
4. Use `docs/*` module documents for subsystem contracts.
5. Inspect `src/<module>/contracts.py` first when implementing or integrating module changes.

This architecture keeps the runtime stable while incrementally layering deterministic, auditable planning and governance intelligence toward a fuller Sentient OS control-plane ecosystem.
