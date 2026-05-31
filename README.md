# Local Autonomous Platform Agent Workspace

REMOTE-AGENTS is the current local-first autonomous runtime foundation for the future Sentient OS backend control plane. Phase 0 keeps the existing worker behavior stable while documenting the contracts that later phases will build on.

## Current Runtime Boundary

The current runtime is:
- local-first
- single-worker
- queue-file driven
- Ollama-compatible by default
- guarded by repository routing and twin approval for selected side-effecting tools

The current runtime does not yet provide:
- distributed queue guarantees
- a Mission DAG Engine
- a Human Approval API
- cloud execution
- multi-worker leases

Those capabilities are planned for later roadmap phases. See `docs/architecture-roadmap.md`.

## Prerequisites

1. Windows 11 on Intel Core Ultra 5 (Meteor Lake)
2. 32GB RAM available
3. Ollama Desktop installed with `qwen2.5-coder:3b` pulled
4. Set the host environment configuration to prevent swapping: `OLLAMA_KEEP_ALIVE=-1`

## Environment Variables

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `PLATFORM_OLLAMA_URL` | `http://localhost:11434/api/generate` | Ollama-compatible generation endpoint used by the platform worker and twin consensus. |
| `PLATFORM_OLLAMA_MODEL` | `qwen2.5-coder:3b` | Local model name used by the platform worker and twin consensus. |
| `PLATFORM_CALLBACK_URL` | unset | Optional HTTP endpoint for completion delivery envelopes. |
| `PLATFORM_CALLBACK_BEARER_TOKEN` | unset | Optional bearer token for callback delivery. |
| `GATEWAY_HOST` | `127.0.0.1` | Gateway bind host. |
| `GATEWAY_PORT` | `8080` | Gateway bind port. |
| `OLLAMA_KEEP_ALIVE` | external Ollama default | Recommended as `-1` for long-lived local operation. |

## Launching the Workspace Engine

To spin up the continuous platform worker loop, execute via your standard development terminal:

```bash
python src/orchastrator/platform_engine.py
```

The legacy typo path above remains supported. New callers may use the canonical alias:

```bash
python src/orchestrator/platform_engine.py
```

To feed the agent a task, drop a JSON packet containing `{"instruction": "your text command here"}` into `.platform_queue/next_task.json`.
Optionally include `target_repository`, for example:

```json
{"instruction":"Update Vite proxy config to point to the new API port","target_repository":"ConceptSHOP"}
```

Alternatively, use the manual dispatcher CLI:

```bash
python src/orchestrator/dispatcher.py --repo "ConceptSHOP" --task "Update Vite proxy config to point to new API port" --priority 2
```

Manual stale-lock prune:

```bash
python src/orchestrator/dispatcher.py --flush-locks
```

On boot, the worker initializes `.platform_queue/` and `.logs/`. Failures are appended to `.logs/errors.json`, and failing payloads are archived to `.platform_queue/failed/` for human review.

## Live Event Ingestion Gateway

For real-time triggers, run the async ingestion gateway:

```bash
python src/orchestrator/gateway.py
```

- `POST /api/v1/trigger` with JSON `{"instruction":"..."}` enqueues a task.
- `GET /health` reports `Idle`, `Processing`, or `Error-Locked`.
- `GET /ws/events` upgrades to WebSocket; each text frame must be JSON containing `{"instruction":"..."}`.

## Terminal Command Center Dashboard

For a live operator view:

```bash
python src/ui/terminal_dashboard.py
```

## Mission Engine MVP

Phase 2 adds a Mission Engine MVP as a control-plane layer above the existing queue. It creates mission/task JSON state under `.missions/` and can adapt the first pending task into the existing `.platform_queue/next_task.json` payload.

It does not replace the current queue or worker.

Single-repository mission:

```bash
python src/mission_engine/cli.py --repo "ConceptSHOP" --title "Fix Vite proxy" --instruction "Update Vite proxy config to point to new API port" --priority 2 --enqueue
```

Multi-repository mission:

```bash
python src/mission_engine/cli.py --repos "Powerframe,PowerStarter" --title "Audit build scripts" --instruction "Audit build scripts and document missing commands" --priority 1 --enqueue
```

See `docs/mission-engine.md` for the contract and compatibility notes.

## Semantic Memory Graph MVP

Phase 4 adds an optional local memory graph at `.memory/graph.json` for mission facts and relationships. It can ingest mission snapshots into repository, task, agent, tool, approval, consensus, artifact, incident, and decision nodes.

This is a seed graph for future Sentient OS Memory Graph UI work. It does not replace `.logs/semantic_memory.json`, and `platform_engine.py` memory injection remains unchanged.

See `docs/semantic-memory-graph.md` for the graph contract, storage shape, ingestion helpers, and query boundary.

## MCP Tool Routing Framework MVP

Phase 5 adds a compatibility-safe tool routing metadata layer. It resolves route plans from `config/registries/tools.json` and `config/platform_mcp_tools.json`, applies policy helper defaults, and can format audit records for future control-plane use.

This does not replace `platform_engine.py` tool execution. Tool invocation still happens in the legacy engine, and the new router is not required at runtime.

See `docs/tool-routing-framework.md` for the route contract, policy defaults, and audit formatting boundary.

## Scheduler Worker Leases MVP

Phase 6 adds local worker descriptors, task lease records, and scheduling planning helpers under `.scheduler/state.json`.

This does not introduce distributed workers, replace `.platform_queue/next_task.json`, or replace `platform_engine.py`. Worker leases are metadata only, intended to prepare Sentient OS views for workers, leases, and queue backpressure.

See `docs/scheduler-worker-leases.md` for the descriptor contracts, lease contracts, local state shape, planner rules, and queue compatibility notes.

## Repository Governance MVP

Phase 7 adds repository governance profiles, health snapshots, audit records, registry import helpers, and policy evaluation metadata under `.governance/repositories.json`.

This does not replace `platform_engine.py`, mutate target repositories, or make governance enforcement mandatory at runtime. It prepares future CI, PR governance, rollback, and Sentient OS Repository Center views.

See `docs/repository-governance.md` for the profile, health, audit, store, import, and policy contracts.

## Control-Plane Exporters MVP

Phase 8 adds read-only control-plane dashboard snapshot exporters for future Sentient OS UI consumption.

This phase does not add an API server. It reads existing local runtime state and writes export artifacts only under `.control_plane/`.

Examples:

```bash
python src/control_plane/cli.py --print
python src/control_plane/cli.py --export
python src/control_plane/cli.py --export-jsonl
```

See `docs/control-plane-exporters.md` for snapshot contracts, collector behavior, and export boundaries.

## Sentient UI Adapter MVP

Phase 9 adds a frontend-ready view-model adapter layer that reads `.control_plane` snapshots and builds typed dashboard panel envelopes for future Sentient-Control-UI integration.

This does not introduce a live API. It reads `.control_plane` files only and writes optional adapter artifacts under `.sentient_ui/`.

Examples:

```bash
python src/sentient_ui/cli.py --print
python src/sentient_ui/cli.py --export
python src/sentient_ui/cli.py --export-jsonl
```

See `docs/sentient-ui-adapter.md` for contracts, trends, panel builders, and exporter behavior.

## Schema Versioning and Migration Dry-Run MVP

Phase 10 adds schema manifests, compatibility check tooling, and migration planning stubs for `.control_plane` and `.sentient_ui` artifacts.

It does not rewrite existing artifacts. Migration remains dry-run only, and reports are written only under `.schema_migrations/`.

Examples:

```bash
python src/schema_versioning/cli.py --check-control-plane
python src/schema_versioning/cli.py --check-sentient-ui
python src/schema_versioning/cli.py --check-file ".control_plane/snapshot.json" --artifact-type control_plane_snapshot
python src/schema_versioning/cli.py --plan-migration ".sentient_ui/view_model.json" --artifact-type sentient_ui_view_model --dry-run
```

See `docs/schema-versioning.md` for manifests, checker behavior, and dry-run migration planning constraints.

## Release Readiness Drift and Reporting MVP

Phase 11 adds read-only contract drift analyzers and release-readiness scoring for control-plane and Sentient UI artifacts.

Reports are advisory only and do not enforce runtime gates in this phase. Report outputs can be written under `.release_reports/`.

Examples:

```bash
python src/release_readiness/cli.py --print
python src/release_readiness/cli.py --export
python src/release_readiness/cli.py --export-jsonl
python src/release_readiness/cli.py --check-file ".control_plane/snapshot.json" --artifact-type control_plane_snapshot
```

See `docs/release-readiness.md` for drift finding types, scoring behavior, and report boundaries.

## Advisory Release Gates MVP

Phase 12 adds configurable advisory gate simulation over release-readiness reports.

This phase does not enforce gates at runtime and does not block mission execution. Optional gate traces are written under `.release_reports/`.

Examples:

```bash
python src/release_gates/cli.py --list-policies
python src/release_gates/cli.py --policy default_gate_policy --print
python src/release_gates/cli.py --policy strict_gate_policy --export
python src/release_gates/cli.py --policy experimental_gate_policy --export-jsonl
```

See `docs/release-gates.md` for policy profile behavior, simulation rules, and trace boundaries.

## Advisory Multi-Policy Scenario Comparison MVP

Phase 13 adds advisory scenario packs for comparing multiple gate policies against the same release-readiness report.

This phase does not enforce release gates and does not block runtime or mission execution. Optional scenario comparison artifacts are written only under `.release_reports/`.

Examples:

```bash
python src/release_gates/cli.py --list-scenarios
python src/release_gates/cli.py --scenario-pack default_release_scenarios --compare --print
python src/release_gates/cli.py --scenario-pack production_release_scenarios --compare --export
python src/release_gates/cli.py --scenario-pack experimental_release_scenarios --compare --export-jsonl
```

See `docs/release-gate-scenarios.md` for strategy behavior, report shape, and comparison boundaries.

## Advisory Release Promotion Planner MVP

Phase 14 adds advisory staged promotion planning for `dev`, `staging`, and `production` using scenario comparison artifacts.

This phase does not deploy, does not enforce gates, does not run CI, and does not run git operations. Optional promotion planning outputs are written only under `.release_reports/`.

Examples:

```bash
python src/release_gates/cli.py --list-promotion-profiles
python src/release_gates/cli.py --profile dev_promotion_profile --plan-promotion --print
python src/release_gates/cli.py --profile staging_promotion_profile --plan-promotion --export
python src/release_gates/cli.py --profile production_promotion_profile --plan-promotion --export-jsonl
python src/release_gates/cli.py --plan-all-promotions --print
```

See `docs/release-promotion-planner.md` for profile thresholds, recommendation behavior, rollback precheck metadata, and CI handoff metadata.

## Advisory Release Center Timeline MVP

Phase 15 adds advisory timeline and milestone synthesis that merges readiness, gate trace, scenario comparison, and promotion recommendation artifacts into a chronological release narrative.

This phase does not enforce gates, does not deploy, does not run CI, does not run git commands, and does not mutate runtime source state. Optional timeline artifacts are written only under `.release_reports/`.

Examples:

```bash
python src/release_center/cli.py --print
python src/release_center/cli.py --export
python src/release_center/cli.py --export-jsonl
python src/release_center/cli.py --label "sentient-os-local-release" --export
```

See `docs/release-center-timeline.md` for event contracts, milestone synthesis, and escalation hint behavior.

## Advisory Capability Matrix and Lifecycle Manager MVP

Phase 16 adds an advisory capability and lifecycle foundation for large-scale agent modeling across repositories.

This phase does not execute agents, does not change runtime behavior, and does not change queue behavior. Optional lifecycle artifacts are written only under `.lifecycle/`.

See `docs/agent-capability-matrix.md` and `docs/lifecycle-manager.md`.

## Advisory Control Plane Orchestration Layer (CPOL)

Phase 17 adds an advisory orchestration layer that links existing control-plane systems in one ordered planning flow:

`mission -> scheduler -> tool_router -> governance -> memory_graph -> release_readiness -> release_gates -> release_center -> lifecycle -> snapshot -> sentient_ui`

This phase does not replace `platform_engine.py`, does not replace `.platform_queue/next_task.json`, and does not enforce gates. It reads advisory artifacts and writes optional orchestration reports only under `.control_plane/orchestration/`.

Examples:

```bash
python src/control_plane/orchestrator_cli.py --print
python src/control_plane/orchestrator_cli.py --export
python src/control_plane/orchestrator_cli.py --export-jsonl
python src/control_plane/orchestrator_cli.py --mission-id "mission_123" --trigger-source manual --print
```

Optional passthrough:

```bash
python src/control_plane/cli.py --run-orchestration --print
```

See `docs/control-plane-orchestration-layer.md`.

## Executive Mission Briefing Layer (EMBL)

Phase 18 adds an advisory executive interpretation layer over CPOL and related control-plane artifacts.

It reads advisory artifacts and produces executive-grade briefings with:
- overall status
- top risks
- blocked items
- recommended next actions
- release/lifecycle/governance summaries

This phase does not execute missions, enforce gates, modify runtime behavior, or change queue semantics.

Examples:

```bash
python src/executive_briefing/cli.py --print
python src/executive_briefing/cli.py --export
python src/executive_briefing/cli.py --export-jsonl
python src/executive_briefing/cli.py --from-orchestration-report ".control_plane/orchestration/orchestration_report.json" --print
```

## Strategic Mission Generation Engine (SMGE)

Phase 19 adds deterministic advisory mission recommendation generation from executive briefing outputs.

It reads executive findings and recommended actions, then produces ranked strategic mission candidates without execution or queue mutation.

Examples:

```bash
python src/strategic_missions/cli.py --print
python src/strategic_missions/cli.py --export
python src/strategic_missions/cli.py --export-jsonl
python src/strategic_missions/cli.py --from-briefing ".control_plane/executive/executive_briefing.json" --limit 5 --print
```

## Repository Intelligence Engine (RIE)

Phase 20 adds deterministic advisory repository intelligence based on actual repository structure and coverage signals.

It scans source, tests, docs, config, runtime entrypoints, and CLI/test alignment, then emits coverage findings and suggested mission opportunities.

Examples:

```bash
python src/repository_intelligence/cli.py --print
python src/repository_intelligence/cli.py --export
python src/repository_intelligence/cli.py --export-jsonl
```

RIE outputs are advisory only and are written under `.control_plane/repository_intelligence/`.

## Repository Remediation Planner (RRP)

Phase 21 converts repository intelligence findings into deterministic advisory remediation items and batches.

It does not execute tasks, does not enqueue anything, and does not mutate `.platform_queue/next_task.json`.

Examples:

```bash
python src/remediation_planner/cli.py --print
python src/remediation_planner/cli.py --export
python src/remediation_planner/cli.py --export-jsonl
python src/remediation_planner/cli.py --from-rie-report ".control_plane/repository_intelligence/repository_intelligence_report.json" --limit 10 --print
```

RRP outputs are advisory only and are written under `.control_plane/remediation_plans/`.

## Remediation Batch Handoff Engine (RBHE)

Phase 22 converts remediation batches into deterministic implementation packages and Codex-ready prompts for manual execution planning.

It does not execute changes, does not enqueue tasks, and does not mutate `.platform_queue`.

Examples:

```bash
python src/remediation_handoff/cli.py --print
python src/remediation_handoff/cli.py --export
python src/remediation_handoff/cli.py --export-jsonl
python src/remediation_handoff/cli.py --limit 2 --print
```

RBHE outputs are advisory only and are written under `.control_plane/remediation_handoffs/`.

## Handoff Package Refinement Engine (HPRE)

Phase 23 refines broad handoff packages into smaller subsystem-scoped and change-type-scoped packages for safer manual implementation.

It does not execute changes, does not enqueue tasks, and does not mutate `.platform_queue`.

Examples:

```bash
python src/handoff_refinement/cli.py --print
python src/handoff_refinement/cli.py --export
python src/handoff_refinement/cli.py --export-jsonl
python src/handoff_refinement/cli.py --from-handoff-report ".control_plane/remediation_handoffs/latest.json"
python src/handoff_refinement/cli.py --limit 5
```

HPRE outputs are advisory only and are written under `.control_plane/handoff_refinements/`.

## Autonomous Work Queue Manager (AWQM)

Phase 24 builds an advisory work queue from refined implementation packages and computes dependency-aware execution ordering with readiness scoring.

It does not execute changes, does not enqueue tasks, and does not mutate `.platform_queue`.

Examples:

```bash
python src/work_queue_manager/cli.py --print
python src/work_queue_manager/cli.py --export
python src/work_queue_manager/cli.py --export-jsonl
python src/work_queue_manager/cli.py --limit 10
```

AWQM outputs are advisory only and are written under `.control_plane/work_queue/`.

## Execution Readiness Dossier Engine (ERDE)

Phase 25 converts prioritized queue items into complete execution dossiers and codex-ready execution packets for manual approval and execution.

It does not execute changes, does not enqueue tasks, and does not mutate `.platform_queue`.

Examples:

```bash
python src/execution_dossier/cli.py --print
python src/execution_dossier/cli.py --export
python src/execution_dossier/cli.py --export-jsonl
python src/execution_dossier/cli.py --from-work-queue ".control_plane/work_queue/latest.json"
python src/execution_dossier/cli.py --limit 10
```

ERDE outputs are advisory only and are written under `.control_plane/execution_dossiers/`.

## Portfolio Orchestration Layer (POL)

Phase 26 extends advisory planning to a multi-repository portfolio view.

POL aggregates repository intelligence, remediation plans, work queue posture, and execution dossier posture into deterministic portfolio scoring and execution-order recommendations.

It does not execute anything, does not enqueue anything, and does not mutate `.platform_queue`.

Examples:

```bash
python src/portfolio_orchestration/cli.py --print
python src/portfolio_orchestration/cli.py --export
python src/portfolio_orchestration/cli.py --export-jsonl
python src/portfolio_orchestration/cli.py --registry ".config/portfolio/portfolio_registry.json"
```

POL outputs are advisory only and are written under `.control_plane/portfolio/`.

## Portfolio Artifact Bootstrap Layer (PABL)

Phase 27 adds deterministic repository onboarding and advisory artifact discovery for portfolio repositories.

PABL inspects repository roots and records advisory artifact coverage without modifying external repositories.

Examples:

```bash
python src/portfolio_bootstrap/cli.py --print
python src/portfolio_bootstrap/cli.py --export
python src/portfolio_bootstrap/cli.py --export-jsonl
```

PABL outputs are advisory only and are written under `.control_plane/portfolio_bootstrap/`.

## Portfolio Onboarding Recommendations (PROR)

Phase 28 converts bootstrap onboarding gaps into deterministic repository-specific onboarding recommendation packages.

Examples:

```bash
python src/portfolio_onboarding_recommendations/cli.py --print
python src/portfolio_onboarding_recommendations/cli.py --export
python src/portfolio_onboarding_recommendations/cli.py --export-jsonl
python src/portfolio_onboarding_recommendations/cli.py --from-bootstrap-report ".control_plane/portfolio_bootstrap/latest.json"
```

PROR outputs are advisory only and are written under `.control_plane/portfolio_onboarding_recommendations/`.

## Portfolio Dependency Intelligence Layer (PDIL)

Phase 29 adds deterministic dependency-aware portfolio governance intelligence.

Examples:

```bash
python src/portfolio_dependencies/cli.py --print
python src/portfolio_dependencies/cli.py --export
python src/portfolio_dependencies/cli.py --export-jsonl
```

PDIL outputs are advisory only and are written under `.control_plane/portfolio_dependencies/`.

## Portfolio Critical Path Intelligence (PCPI)

Phase 30 adds deterministic critical-path analysis for highest-leverage portfolio actions.

Examples:

```bash
python src/portfolio_critical_path/cli.py --print
python src/portfolio_critical_path/cli.py --export
python src/portfolio_critical_path/cli.py --export-jsonl
```

PCPI outputs are advisory only and are written under `.control_plane/portfolio_critical_path/`.

## Portfolio Strategic Execution Roadmap Layer (PSERL)

Phase 31 converts critical-path findings into deterministic near-term, mid-term, and long-term portfolio execution waves.

Examples:

```bash
python src/portfolio_roadmap/cli.py --print
python src/portfolio_roadmap/cli.py --export
python src/portfolio_roadmap/cli.py --export-jsonl
```

PSERL outputs are advisory only and are written under `.control_plane/portfolio_roadmap/`.

## Portfolio Progress Intelligence Layer (PPIL)

Phase 32 adds deterministic progress tracking over portfolio, onboarding, dependency, critical-path, and roadmap artifacts.

Examples:

```bash
python src/portfolio_progress/cli.py --print
python src/portfolio_progress/cli.py --export
python src/portfolio_progress/cli.py --export-jsonl
```

PPIL outputs are advisory only and are written under `.control_plane/portfolio_progress/`.

## Portfolio Drift Intelligence Layer (PDIL-2)

Phase 33 adds deterministic cross-artifact drift detection across the portfolio governance stack.

Examples:

```bash
python src/portfolio_drift/cli.py --print
python src/portfolio_drift/cli.py --export
python src/portfolio_drift/cli.py --export-jsonl
```

PDIL-2 outputs are advisory only and are written under `.control_plane/portfolio_drift/`.

## Handoff Package Refinement Engine (HPRE)

Phase 23 refines broad handoff packages into smaller subsystem-scoped packages with focused validation plans and smaller Codex prompts.

It does not execute changes, does not enqueue tasks, and does not mutate `.platform_queue`.

Examples:

```bash
python src/handoff_refinement/cli.py --print
python src/handoff_refinement/cli.py --export
python src/handoff_refinement/cli.py --export-jsonl
python src/handoff_refinement/cli.py --from-handoff-report ".control_plane/remediation_handoffs/latest.json"
python src/handoff_refinement/cli.py --limit 5
```

HPRE outputs are advisory only and are written under `.control_plane/handoff_refinements/`.

## Runtime Contracts

See `docs/runtime-contracts.md` for the Phase 0 contracts covering:
- `.platform_queue/next_task.json`
- `.platform_queue/processing.lock`
- `.platform_queue/failed/`
- gateway HTTP and WebSocket endpoints
- `config/agent_registry.json`
- `config/platform_mcp_tools.json`
- twin consensus approval flow

## Roadmap and Decisions

- `docs/architecture-roadmap.md` records the current Phase 0 boundary and later planned phases.
- `docs/decisions.md` records Phase 0 architecture decisions.
- `docs/registry-architecture.md` records the Phase 1 registry structure.
- `docs/mission-engine.md` records the Phase 2 and Phase 3 mission state boundary.
- `docs/semantic-memory-graph.md` records the Phase 4 optional graph memory boundary.
- `docs/tool-routing-framework.md` records the Phase 5 route planning boundary.
- `docs/scheduler-worker-leases.md` records the Phase 6 scheduler metadata boundary.
- `docs/repository-governance.md` records the Phase 7 governance metadata boundary.
- `docs/control-plane-exporters.md` records the Phase 8 control-plane export boundary.
- `docs/sentient-ui-adapter.md` records the Phase 9 Sentient UI adapter boundary.
- `docs/schema-versioning.md` records the Phase 10 schema compatibility and dry-run migration boundary.
- `docs/release-readiness.md` records the Phase 11 advisory release-readiness boundary.
- `docs/release-gates.md` records the Phase 12 advisory gate simulation boundary.
- `docs/release-gate-scenarios.md` records the Phase 13 advisory multi-policy comparison boundary.
- `docs/release-promotion-planner.md` records the Phase 14 advisory staged promotion planning boundary.
- `docs/release-center-timeline.md` records the Phase 15 advisory timeline synthesis boundary.
- `docs/agent-capability-matrix.md` and `docs/lifecycle-manager.md` record the Phase 16 advisory lifecycle and capability matrix boundary.
- `docs/control-plane-orchestration-layer.md` records the Phase 17 advisory orchestration boundary.
- `docs/repository-intelligence-engine.md` records the Phase 20 advisory repository intelligence boundary.
- `docs/repository-remediation-planner.md` records the Phase 21 advisory remediation planning boundary.
- `docs/remediation-batch-handoff-engine.md` records the Phase 22 advisory remediation handoff boundary.
- `docs/handoff-package-refinement-engine.md` records the Phase 23 advisory handoff refinement boundary.
- `docs/autonomous-work-queue-manager.md` records the Phase 24 advisory work queue boundary.
- `docs/execution-readiness-dossier-engine.md` records the Phase 25 advisory execution dossier boundary.
- `docs/portfolio-orchestration-layer.md` records the Phase 26 advisory portfolio orchestration boundary.
- `docs/portfolio-artifact-bootstrap-layer.md` records the Phase 27 advisory portfolio onboarding and artifact discovery boundary.
- `docs/portfolio-onboarding-recommendations.md` records the Phase 28 advisory onboarding recommendation boundary.
- `docs/portfolio-dependency-intelligence-layer.md` records the Phase 29 advisory dependency intelligence boundary.
- `docs/portfolio-critical-path-intelligence.md` records the Phase 30 advisory critical-path intelligence boundary.
- `docs/portfolio-strategic-execution-roadmap.md` records the Phase 31 advisory strategic execution roadmap boundary.
- `docs/portfolio-progress-intelligence-layer.md` records the Phase 32 advisory portfolio progress boundary.
- `docs/portfolio-drift-intelligence-layer.md` records the Phase 33 advisory portfolio drift boundary.
- `docs/handoff-package-refinement-engine.md` records the Phase 23 advisory refinement boundary.

## Additional Repository Components

- Office runtime entrypoint: `run_autonomous_office.py`
- 3D dashboard frontend: `packages/dashboard-3d/`
- Backend bridge module: `core/mcp_bridge.py`
- Integration rig: `tests/test_3d_canvas_integration.py`
