# Decisions

## ADR-0001: Preserve Legacy Platform Engine Path

Date: 2026-05-29

Decision:
- Keep `src/orchastrator/platform_engine.py` as the existing implementation path.
- Add `src/orchestrator/platform_engine.py` as the canonical entrypoint.
- The canonical entrypoint delegates to the legacy implementation.

Reason:
- Existing launch commands and scripts continue to work.
- New callers have a correctly spelled path.
- The change is small and reversible.

Consequences:
- Both commands are valid during Phase 0.
- Future cleanup can move the implementation after compatibility windows are defined.

## ADR-0002: Document Current Contracts Before Re-Architecture

Date: 2026-05-29

Decision:
- Capture queue, lock, gateway, registry, tool, and twin approval contracts in `docs/runtime-contracts.md`.
- Keep implementation behavior unchanged except environment variable defaults for Ollama configuration.

Reason:
- The runtime needs stable surfaces before Phase 1 registry work and later Mission Engine work.

Consequences:
- Future changes can be reviewed against explicit contracts.
- Phase 0 avoids introducing distributed workers, cloud execution, or mission DAG behavior.

## ADR-0003: Local-First Single-Worker Boundary

Date: 2026-05-29

Decision:
- State clearly that the current runtime is local-first and single-worker.
- Treat distributed queue guarantees, Mission DAGs, and Human Approval APIs as later-phase work.

Reason:
- The repository already contains advanced primitives, but the live runtime should not claim guarantees it does not yet provide.

Consequences:
- Operator expectations are clearer.
- Later phases can integrate existing `core/` primitives deliberately.

## ADR-0004: Add Canonical Registries Without Runtime Migration

Date: 2026-05-29

Decision:
- Add canonical seed registries under `config/registries/`.
- Keep `config/agent_registry.json` as the live runtime registry for Phase 1.
- Validate canonical registries with lightweight tests instead of introducing a new runtime loader.

Reason:
- The future Agent Operating System needs structured repository, agent, tool, model, and policy data.
- The current worker must remain compatibility-safe while that structure is introduced.

Consequences:
- Runtime behavior is unchanged.
- `src/routers/repo_governance_router.py` continues to load the legacy registry as before.
- Later phases can migrate runtime loading deliberately after schemas and compatibility rules settle.

## ADR-0005: Add Mission Engine as a Layer Above the Legacy Queue

Date: 2026-05-29

Decision:
- Add `src/mission_engine/` as a standalone Mission Engine MVP.
- Store missions as JSON files under `.missions/`.
- Plan tasks through the existing repository governance router.
- Adapt mission tasks into `.platform_queue/next_task.json` without replacing queue behavior.

Reason:
- Sentient OS needs durable mission/task state before richer scheduling exists.
- The current local worker remains the only execution runtime in Phase 2.

Consequences:
- `platform_engine.py` remains unchanged.
- The Mission Engine can create and enqueue compatible work, but it does not run a daemon.
- If the legacy queue slot is occupied, the adapter blocks safely instead of overwriting it.
- Distributed scheduling remains deferred to Phase 6.

## ADR-0006: Record Approvals and Consensus Without Enforcement

Date: 2026-05-29

Decision:
- Add approval and consensus record contracts to mission state.
- Extend `MissionStore` with append-only approval and consensus methods.
- Keep these records as durable JSON evidence only in Phase 3.

Reason:
- Future Human Approval and Consensus services need stable record shapes.
- The current runtime already has a twin approval gate in `platform_engine.py`; replacing it now would risk compatibility.

Consequences:
- Human approval records can be created and persisted, but they do not block or permit execution yet.
- Consensus records can capture twin, quorum, human, policy, or system decisions.
- `platform_engine.py` remains the runtime authority for existing write/execute twin checks.
- Enforcement is deferred to a later approval service phase.

## ADR-0007: Add Optional Local Semantic Memory Graph

Date: 2026-05-29

Decision:
- Add `src/memory_graph/` as a local Semantic Memory Graph MVP.
- Store graph state as JSON at `.memory/graph.json`.
- Provide mission ingestion helpers and simple in-memory query helpers.
- Keep graph ingestion optional and out of the existing runtime execution path.

Reason:
- Sentient OS needs durable relationship memory for missions, repositories, agents, tools, approvals, consensus, incidents, and decisions.
- The existing `.logs/semantic_memory.json` path is still the active runtime memory surface, and replacing it now would risk compatibility.

Consequences:
- `platform_engine.py` memory injection remains unchanged.
- `.logs/semantic_memory.json` behavior remains unchanged.
- The graph can be populated by explicit helpers, but mission creation and queue adaptation do not require it.
- Future phases can connect graph memory to the planner, agents, policy checks, and Sentient OS Memory Graph UI after the seed contract stabilizes.

## ADR-0008: Add Tool Routing Metadata Without Runtime Invocation

Date: 2026-05-29

Decision:
- Add `src/tool_router/` as a compatibility-safe MCP Tool Routing Framework MVP.
- Resolve route metadata from `config/registries/tools.json` and `config/platform_mcp_tools.json`.
- Return disabled high-risk fallback routes for unknown or unavailable tools.
- Add policy helper functions and audit record formatting without invoking tools or persisting audit records.

Reason:
- Sentient OS needs a future tool control plane with provider, risk, approval, network, write, and repository-boundary metadata.
- The current worker already executes tools through `platform_engine.py`; changing that path now would exceed Phase 5 and risk compatibility.

Consequences:
- `platform_engine.py` remains the live tool execution path.
- `.platform_queue/next_task.json` behavior remains unchanged.
- The new router can be used by tests, docs, and future planning layers, but it is not required at runtime.
- Future phases can connect the router to the Agent Runtime, Approval Service, Mission Engine, and Sentient OS Tool Center.

## ADR-0009: Add Local Scheduler Metadata Without Distributed Execution

Date: 2026-05-29

Decision:
- Add `src/scheduler/` as a local scheduler metadata MVP.
- Store worker descriptors, leases, and scheduler events in `.scheduler/state.json`.
- Add planning helpers that select candidate workers or return blocked schedule decisions.
- Add read-only helpers for explaining the legacy single-file queue and processing lock.

Reason:
- Sentient OS needs a foundation for visualizing workers, leases, and backpressure before real distributed execution exists.
- The current runtime still depends on `.platform_queue/next_task.json`; replacing that queue now would exceed Phase 6.

Consequences:
- `platform_engine.py` remains unchanged.
- `.platform_queue/next_task.json` remains the only live queue slot.
- Worker leases are metadata only and do not grant runtime execution rights.
- Real distributed scheduling, durable distributed queues, and cloud execution remain future work.

## ADR-0010: Add Repository Governance Metadata Without Enforcement

Date: 2026-05-29

Decision:
- Add `src/repository_governance/` as a repository governance metadata MVP.
- Store governance profiles, health snapshots, and audit records in `.governance/repositories.json`.
- Import profile seeds from `config/registries/repositories.json` without modifying that registry.
- Add advisory policy evaluation helpers that return audit records instead of enforcing runtime gates.

Reason:
- Sentient OS needs enterprise repository governance visibility before CI, PR, rollback, and Repository Center workflows become active.
- The current runtime already routes work through `platform_engine.py` and the single-file queue; making governance mandatory now would risk compatibility.

Consequences:
- `platform_engine.py` remains unchanged.
- `.platform_queue/next_task.json` remains unchanged.
- Target repositories are not mutated by Phase 7 helpers.
- Governance decisions are durable metadata and planning signals only.
- Mandatory enforcement, CI/PR governance, rollback automation, and Sentient OS Repository Center views remain future work.

## ADR-0011: Add Read-Only Control-Plane Snapshot Exporters

Date: 2026-05-29

Decision:
- Add `src/control_plane/` with snapshot contracts, collectors, builders, and CLI exporters.
- Collect read-only metadata from existing runtime state files.
- Export snapshots to `.control_plane/snapshot.json` and `.control_plane/snapshots.jsonl`.
- Keep exports one-shot and local; no server, daemon, or network dependency.

Reason:
- Sentient OS and Sentient-Control-UI need a stable snapshot feed before API or streaming layers are introduced.
- Current runtime compatibility must be preserved while enabling dashboard seed data.

Consequences:
- `platform_engine.py` remains unchanged.
- `.platform_queue/next_task.json` behavior remains unchanged.
- Source state remains read-only for collection.
- Only `.control_plane/` export artifacts are written.
- API server delivery and real-time control-plane transport remain future work.

## ADR-0012: Add Sentient UI View Model Adapter Without API Serving

Date: 2026-05-29

Decision:
- Add `src/sentient_ui/` with contracts, snapshot readers, trend helpers, panel builders, exporters, and CLI.
- Read only from `.control_plane/snapshot.json` and `.control_plane/snapshots.jsonl`.
- Write optional UI artifacts only under `.sentient_ui/`.
- Keep adapter execution one-shot and local with no daemon or web server.

Reason:
- Sentient-Control-UI needs frontend-ready view models before live API and streaming layers are introduced.
- The runtime control plane must remain compatibility-safe and unchanged.

Consequences:
- `platform_engine.py` remains unchanged.
- `.platform_queue/next_task.json` behavior remains unchanged.
- Runtime source state remains read-only for this phase.
- Future UI layers can ingest `.sentient_ui` artifacts directly.
- API serving and live push subscriptions remain future work.

## ADR-0013: Add Schema Versioning and Dry-Run Migration Planning

Date: 2026-05-29

Decision:
- Add `src/schema_versioning/` for schema manifests, compatibility check results, and migration plan contracts.
- Add compatibility checker helpers for `.control_plane` and `.sentient_ui` artifacts.
- Add migration planning stubs that do not perform in-place rewrites.
- Allow dry-run report output only under `.schema_migrations/`.

Reason:
- Sentient OS contract evolution needs explicit schema governance before managed migrations or API version routing is introduced.
- Existing runtime and adapter behavior must remain compatibility-safe and non-destructive.

Consequences:
- `platform_engine.py` remains unchanged.
- `.platform_queue/next_task.json` remains unchanged.
- Source `.control_plane` and `.sentient_ui` artifacts remain unchanged in Phase 10.
- Migration actions remain planning-only and dry-run.
- Future phases can promote these checks into automated upgrade and rollout workflows.

## ADR-0014: Add Advisory Contract Drift and Release Readiness Reports

Date: 2026-05-29

Decision:
- Add `src/release_readiness/` for read-only drift analysis and readiness scoring.
- Compare artifacts against schema manifests and compatibility check outputs.
- Publish advisory release-readiness reports under `.release_reports/`.
- Keep reports non-blocking and non-enforcing in this phase.

Reason:
- Sentient OS rollout needs a clear pre-release signal before introducing mandatory gates.
- Existing runtime behavior must remain unchanged while contract quality signals mature.

Consequences:
- `platform_engine.py` remains unchanged.
- `.platform_queue/next_task.json` remains unchanged.
- Source artifacts are not rewritten by Phase 11 tooling.
- Reports provide actionable visibility but do not block execution yet.
- Future phases can convert advisory reports into optional or mandatory release gates.

## ADR-0015: Add Advisory Gate Simulation with Policy Threshold Profiles

Date: 2026-05-29

Decision:
- Add `config/release_gates/` policy profiles for default, strict, and experimental advisory simulation.
- Add `src/release_gates/` to simulate gate decisions from release-readiness reports.
- Add dry-run trace output under `.release_reports/` only.
- Keep all gate outputs advisory and non-enforcing in Phase 12.

Reason:
- Teams need policy-tunable pre-release guidance before promoting gates into hard CI/runtime controls.
- Runtime compatibility and execution flow must remain unchanged.

Consequences:
- `platform_engine.py` remains unchanged.
- `.platform_queue/next_task.json` remains unchanged.
- No runtime gate enforcement is introduced.
- Gate decisions are guidance artifacts only.
- Future phases can safely promote simulated policies to CI/pre-release enforcement.

## ADR-0016: Add Advisory Multi-Policy Scenario Comparison

Date: 2026-05-29

Decision:
- Add scenario pack metadata under `config/release_gates/scenario_packs/`.
- Add `src/release_gates/` scenario contracts, loader, multi-policy simulator, and scenario report writers.
- Extend the release gate CLI with scenario list and compare/export commands.
- Keep scenario outputs advisory-only with no runtime enforcement.

Reason:
- Release teams need policy composition and what-if comparisons across default, strict, and experimental gate thresholds.
- Comparing multiple policy outcomes on one readiness report reduces ambiguity before future CI gate promotion.

Consequences:
- `platform_engine.py` remains unchanged.
- `.platform_queue/next_task.json` remains unchanged.
- Runtime and mission execution are never blocked by Phase 13 tooling.
- Scenario artifacts are written only under `.release_reports/`.
- Future Sentient OS Release Center views can consume scenario comparison artifacts directly.

## ADR-0017: Add Advisory Staged Promotion Planning

Date: 2026-05-29

Decision:
- Add promotion profile metadata under `config/release_gates/promotion_profiles/`.
- Add `src/release_gates/` promotion contracts, loader, planner, rollback precheck metadata, CI handoff metadata, and report writers.
- Extend release gate CLI with promotion profile list and promotion planning/export commands.
- Keep recommendations advisory-only with no deployment, gate enforcement, CI execution, or git operations.

Reason:
- Release operators need staged, explainable promotion guidance across `dev`, `staging`, and `production` before hard enforcement.
- Promotion decisions need explicit rollback/CI handoff metadata to prepare future Release Center workflows.

Consequences:
- `platform_engine.py` remains unchanged.
- `.platform_queue/next_task.json` remains unchanged.
- Runtime source state remains unchanged by promotion tooling.
- Promotion artifacts are written only under `.release_reports/`.
- Future phases can promote advisory planning outputs into CI-integrated and policy-enforced release workflows.

## ADR-0018: Add Advisory Release Center Timeline Synthesis

Date: 2026-05-29

Decision:
- Add `src/release_center/` for timeline contracts, artifact readers, timeline synthesis, milestone synthesis, and report exports.
- Synthesize chronological release events from readiness, gate, scenario, and promotion artifacts.
- Generate milestone states, owner placeholders, and escalation hints as advisory metadata.
- Add CLI exports under `.release_reports/` only.

Reason:
- Operators need a single advisory release narrative to understand readiness progression and promotion risk across environments.
- Future Sentient OS Release Center views need a stable local artifact feed before any live API layer.

Consequences:
- `platform_engine.py` remains unchanged.
- `.platform_queue/next_task.json` remains unchanged.
- No gate enforcement, deployment, CI execution, or git operations are introduced.
- Source artifacts remain unchanged; only timeline outputs are written under `.release_reports/`.

## ADR-0019: Add Advisory Capability Matrix and Lifecycle Foundation

Date: 2026-05-29

Decision:
- Add `src/lifecycle_manager/` contracts, capability profile inference, lifecycle store/state helpers, and health scoring/gap detection.
- Keep lifecycle artifacts local under `.lifecycle/`.
- Add optional adapters for control-plane and Sentient UI lifecycle summaries without replacing existing runtime collectors.

Reason:
- The platform needs a structured foundation for modeling 100+ agents across 50+ repositories before introducing runtime lifecycle orchestration.

Consequences:
- Runtime execution remains unchanged.
- Queue behavior remains unchanged.
- No agent execution or queue mutation is introduced.
- Lifecycle outputs are advisory and local-only.

## ADR-0020: Add Advisory Control Plane Orchestration Layer (CPOL)

Date: 2026-05-30

Decision:
- Add `src/control_plane/orchestrator_contracts.py` for orchestration request/stage/report contracts.
- Add `src/control_plane/orchestrator.py` to run ordered advisory stage wrappers across existing control-plane subsystems.
- Add `src/control_plane/orchestrator_reports.py` for atomic JSON and append-only JSONL report exports under `.control_plane/orchestration/`.
- Add `src/control_plane/orchestrator_cli.py` for on-demand advisory orchestration report generation.
- Keep stage wrappers read-only and tolerant of missing artifacts (`not_run`/`warning`) instead of failing hard.

Reason:
- Existing advisory systems are complete but fragmented. A thin orchestration layer provides one coherent planning workflow without introducing runtime coupling or enforcement.

Consequences:
- `platform_engine.py` execution flow remains unchanged.
- `.platform_queue/next_task.json` semantics remain unchanged.
- No gate enforcement, queue mutation, mission execution, or agent execution is introduced.
- Orchestration outputs are advisory artifacts only, written under `.control_plane/orchestration/`.

## ADR-0021: Add Advisory Executive Mission Briefing Layer (EMBL)

Date: 2026-05-30

Decision:
- Add `src/executive_briefing/` with advisory contracts, deterministic analysis, briefing builder, report writers, and CLI.
- Consume existing advisory artifacts only: CPOL reports, release readiness, gate traces, release center timelines, lifecycle state, control-plane snapshot, and Sentient UI view-model exports.
- Export executive briefing artifacts under `.control_plane/executive/`.
- Add optional Sentient UI executive panel adapters in `src/sentient_ui/executive_panels.py`.

Reason:
- CPOL already produces stage-level orchestration health; operators need executive interpretation across systems without introducing runtime enforcement.

Consequences:
- Runtime execution remains unchanged.
- Queue semantics remain unchanged.
- No deployments, git operations, CI execution, or enforcement behavior is introduced.
- Executive outputs are deterministic, advisory-only, and suitable for future Sentient OS executive views.

## ADR-0022: Add Advisory Strategic Mission Generation Engine (SMGE)

Date: 2026-05-31

Decision:
- Add `src/strategic_missions/` for deterministic strategic mission candidate generation from executive briefings.
- Add explicit strategic mission contracts and scoring/priority mapping.
- Add report export support under `.control_plane/strategic_missions/`.
- Keep generation advisory-only, with no queue writes and no automatic mission enqueue.

Reason:
- Executive findings need a deterministic planning bridge into actionable mission recommendations while preserving runtime compatibility.

Consequences:
- `platform_engine.py` remains unchanged.
- `.platform_queue/next_task.json` semantics remain unchanged.
- No execution, enforcement, deployment, git operations, or cloud behavior is introduced.
- Outputs are planning artifacts only for future operator-driven mission selection.

## ADR-0023: Add Advisory Repository Intelligence Engine (RIE)

Date: 2026-05-31

Decision:
- Add `src/repository_intelligence/` with contracts, deterministic scanner/analyzer, report writers, and CLI.
- Scan current repository structure only (source/tests/docs/config/runtime entrypoints) with strict ignore rules for generated/runtime output folders.
- Export intelligence artifacts under `.control_plane/repository_intelligence/`.
- Integrate optionally with executive briefing and strategic mission generation when a latest intelligence report exists.

Reason:
- Strategic planning quality improves when mission recommendations are grounded in observable repository coverage gaps, not only control-plane telemetry.

Consequences:
- Runtime execution remains unchanged.
- Queue semantics remain unchanged.
- No enforcement, deployment, cloud, git, or model-call behavior is introduced.
- Repository intelligence remains advisory-only and optional.

## ADR-0024: Add Advisory Repository Remediation Planner (RRP)

Date: 2026-05-31

Decision:
- Add `src/remediation_planner/` contracts, deterministic scoring, remediation planning, report writers, and CLI.
- Consume repository intelligence artifacts and generate advisory remediation items/batches only.
- Export remediation artifacts under `.control_plane/remediation_plans/` as latest JSON, timestamped JSON, and JSONL history.
- Integrate optionally:
  - Strategic missions ingest high-priority remediation batches when report exists.
  - Executive briefing flags high-priority remediation backlog risk when report exists.

Reason:
- Repository intelligence findings need a deterministic, operator-readable remediation bridge before mission execution decisions are made.

Consequences:
- `platform_engine.py` remains unchanged.
- `.platform_queue/next_task.json` semantics remain unchanged.
- No auto-enqueue, execution, enforcement, deployment, git, cloud, or model-call behavior is introduced.
- Remediation planning remains advisory-only and optional.
