# Architecture Roadmap

## Phase 0: Runtime Stabilization

Status: complete.

Phase 0 preserves the existing local runtime and makes it easier to build on:
- Keep the legacy `src/orchastrator/platform_engine.py` command working.
- Add the canonical `src/orchestrator/platform_engine.py` entrypoint.
- Document queue, gateway, registry, tool, and twin approval contracts.
- Normalize environment variable documentation.
- State current architectural limits clearly.

## Current Architecture Boundary

REMOTE-AGENTS is currently a local-first, single-worker runtime.

Current guarantees:
- One on-disk task slot at `.platform_queue/next_task.json`.
- One processing lock at `.platform_queue/processing.lock`.
- Local Ollama-compatible model calls.
- Repository routing through `config/agent_registry.json`.
- Twin approval for selected side-effecting tools.
- Best-effort health telemetry and failure archives.

Current non-goals:
- No distributed queue guarantees yet.
- No Mission DAG Engine yet.
- No Human Approval API yet.
- No cloud execution layer yet.
- No multi-worker lease scheduler yet.

## Later Phases

Phase 1: Canonical registries.
Status: complete.

- Split repository, agent, tool, model, and policy concerns into explicit schemas.
- Convert guide data into structured seed records.
- Add repository governance profiles.
- Preserve `config/agent_registry.json` as the live runtime registry.
- Add compatibility validation in `tests/test_registry_contracts.py`.

Phase 2: Mission Engine MVP.
Status: complete.

- Introduce durable mission and task state.
- Decompose instructions into mission stages.
- Use DAG/checkpoint/proof-ledger primitives through one control plane.
- Add a compatibility-safe queue adapter that emits the existing `.platform_queue/next_task.json` payload shape.
- Keep distributed scheduling, Human Approval APIs, and cloud execution out of scope.

Phase 3: Approval and Consensus.
Status: complete.

- Add durable approval records to mission JSON.
- Add durable consensus records to mission JSON.
- Keep Phase 3 as recordkeeping only; runtime enforcement remains unchanged.
- Defer mandatory human approval gates to a later approval service phase.

Phase 4: Semantic Memory Graph.
Status: complete.

- Add a local seed graph at `.memory/graph.json`.
- Model missions, tasks, repositories, agents, tools, approvals, consensus records, artifacts, incidents, and decisions.
- Keep graph ingestion optional and separate from runtime execution.
- Keep `.logs/semantic_memory.json` and `platform_engine.py` memory injection unchanged.
- Defer graph-backed retrieval, planner integration, and Sentient OS Memory Graph UI to later phases.

Phase 5: MCP Tool Router and Provider Abstraction.
Status: complete.

- Add a compatibility-safe `src/tool_router/` route planning layer.
- Normalize canonical and legacy tool metadata into structured routes.
- Add policy helpers for approval, network, write, repository-boundary, and runtime-context planning.
- Add audit record formatting without persistent audit storage.
- Keep `platform_engine.py` as the only live tool execution path.
- Defer runtime enforcement and Sentient OS Tool Center integration to later phases.

Phase 6: Local Worker Leases and Scheduling Metadata.
Status: complete.

- Add local worker descriptor contracts.
- Add task lease contracts and `.scheduler/state.json` metadata storage.
- Add scheduler planning helpers that select compatible workers or return blocked plans.
- Add read-only legacy queue compatibility helpers for backpressure visibility.
- Keep `.platform_queue/next_task.json` and `platform_engine.py` unchanged.
- Defer real distributed workers, durable distributed queues, and cloud execution to later phases.

Phase 7: Enterprise Governance and Scale.
Status: complete.

- Add repository governance profile contracts.
- Add repository health snapshot contracts.
- Add repository audit record contracts and local `.governance/repositories.json` storage.
- Add import helpers from the canonical repositories registry.
- Add advisory policy evaluation metadata for allowed, denied, approval-needed, and review-needed decisions.
- Keep runtime execution unchanged and defer mandatory enforcement, CI/PR governance, rollback automation, and Repository Center views to later phases.

Phase 8: Control-Plane Snapshot Exporters.
Status: complete.

- Add `src/control_plane/` read-only collectors for runtime, missions, registries, governance, scheduler, tool routes, memory graph, approvals/consensus, and observability.
- Add control-plane snapshot contracts and builders.
- Add one-shot CLI exporters for snapshot print, JSON export, and JSONL append.
- Keep reads against existing runtime state only.
- Write snapshot artifacts only under `.control_plane/`.
- Defer API server exposure and live streaming telemetry to later phases.

Phase 9: Sentient UI Adapter Layer.
Status: complete.

- Add `src/sentient_ui/` contracts for typed panel and envelope view models.
- Add snapshot readers and history trend aggregation helpers.
- Add panel builders for runtime, missions, agents, repositories, tools, scheduler, memory, approvals, consensus, and observability.
- Add optional `.sentient_ui/` exporters and a one-shot CLI.
- Keep reads limited to `.control_plane` snapshot files.
- Defer live API serving and streaming UI updates to later phases.

Phase 10: Schema Versioning and Migration Dry-Run.
Status: complete.

- Add `src/schema_versioning/` contracts for manifests, compatibility checks, and migration plans.
- Add schema manifests for control-plane and Sentient UI v1 artifacts.
- Add read-only compatibility checker tooling for JSON and JSONL artifacts.
- Add dry-run migration planner stubs with report output under `.schema_migrations/`.
- Keep source artifacts unchanged and avoid destructive migration.

Phase 11: Contract Drift and Release Readiness Reporting.
Status: complete.

- Add `src/release_readiness/` contracts for drift findings and release-readiness reports.
- Add read-only drift analyzers for control-plane, Sentient UI, JSONL histories, and schema manifests.
- Add readiness scoring and status classification helpers.
- Add advisory report writers under `.release_reports/`.
- Keep runtime source artifacts unchanged and avoid enforcement gates in this phase.

Phase 12: Advisory Gate Simulation and Policy Profiles.
Status: complete.

- Add `config/release_gates/` threshold policy profiles.
- Add `src/release_gates/` contracts, policy loader, simulator, trace writers, and CLI.
- Simulate gate outcomes from release-readiness reports without enforcing runtime gates.
- Write optional gate traces under `.release_reports/` only.
- Defer actual CI/runtime gate enforcement to future phases.

Phase 13: Multi-Policy Scenario Packs and Comparison Reports.
Status: complete.

- Add scenario pack configs under `config/release_gates/scenario_packs/`.
- Add scenario contracts, loader, and multi-policy simulator helpers.
- Add aggregate strategies: `compare_all`, `strictest_wins`, `permissive_preview`, and `production_candidate`.
- Add scenario comparison report writers under `.release_reports/`.
- Extend release gate CLI with scenario listing and compare/export commands.
- Keep all outputs advisory-only with no runtime enforcement.

Phase 14: Advisory Staged Promotion Planning.
Status: complete.

- Add promotion profiles for `dev`, `staging`, and `production`.
- Add promotion contracts, loader, planner, rollback precheck metadata, and CI handoff metadata builders.
- Add promotion report writers under `.release_reports/`.
- Extend release gate CLI with profile listing and promotion planning/export modes.
- Keep all outputs advisory-only; no deployment, runtime enforcement, CI execution, or git operations.

Phase 15: Advisory Release Center Timeline Synthesis.
Status: complete.

- Add `src/release_center/` contracts, artifact readers, timeline synthesizer, milestone synthesizer, report writers, and CLI.
- Merge readiness, gate, scenario, and promotion artifacts into chronological release narratives.
- Generate milestone states, owner placeholders, and escalation hints for dev/staging/production promotion paths.
- Export advisory timeline artifacts only under `.release_reports/`.
- Keep runtime execution and queue behavior unchanged with no enforcement or deployment behavior.

Phase 16: Advisory Agent Capability Matrix and Lifecycle Foundation.
Status: complete.

- Add `src/lifecycle_manager/` capability contracts, lifecycle contracts, registry builder, store, health scoring, and lifecycle helpers.
- Add advisory coverage and gap detection for repository-to-agent mappings.
- Add optional control-plane and Sentient UI lifecycle adapters without changing existing runtime contracts.
- Keep execution, queue behavior, and platform engine runtime flow unchanged.

Phase 17: Advisory Control Plane Orchestration Layer (CPOL).
Status: complete.

- Add `src/control_plane/orchestrator_contracts.py` request/stage/report contracts with `advisory_only=true` validation.
- Add `src/control_plane/orchestrator.py` ordered advisory stage flow:
  `mission -> scheduler -> tool_router -> governance -> memory_graph -> release_readiness -> release_gates -> release_center -> lifecycle -> snapshot -> sentient_ui`.
- Add report writers in `src/control_plane/orchestrator_reports.py` that write only under `.control_plane/orchestration/`.
- Add `src/control_plane/orchestrator_cli.py` for print/export/export-jsonl report modes with optional mission context.
- Keep missing artifacts non-fatal (`warning`/`not_run`) to preserve local compatibility.
- Keep `platform_engine.py` and `.platform_queue/next_task.json` runtime behavior unchanged.

Phase 18: Executive Mission Briefing Layer (EMBL).
Status: complete.

- Add `src/executive_briefing/` contracts, deterministic analyzer, briefing builder, report writers, and CLI.
- Consume advisory artifacts from CPOL, release readiness, release gates, release center, lifecycle, control-plane snapshots, and Sentient UI exports.
- Produce executive-grade advisory outputs (summary, top risks, blocked items, and recommended actions).
- Export optional artifacts under `.control_plane/executive/`.
- Add optional Sentient UI executive panels through `src/sentient_ui/executive_panels.py`.
- Keep runtime execution, queue behavior, and enforcement unchanged.

Phase 19: Strategic Mission Generation Engine (SMGE).
Status: complete.

- Add `src/strategic_missions/` contracts, deterministic scoring, candidate generator, report writers, and CLI.
- Convert executive briefing findings and recommended actions into ranked advisory strategic mission candidates.
- Generate maintenance/continuity recommendations when executive status is healthy with no risks.
- Export optional outputs under `.control_plane/strategic_missions/`.
- Keep queue semantics unchanged and never auto-enqueue mission candidates.

Phase 20: Repository Intelligence Engine (RIE).
Status: complete.

- Add `src/repository_intelligence/` contracts, scanner, analyzer, reports, and CLI.
- Generate deterministic advisory repository intelligence reports from repository structure, docs, tests, config, runtime entrypoints, and contract/test coverage signals.
- Write optional latest, timestamped, and JSONL outputs under `.control_plane/repository_intelligence/`.
- Add optional integration:
  - Executive Briefing ingests high/critical repository intelligence findings when report is present.

Phase 21: Repository Remediation Planner (RRP).
Status: complete.

- Add `src/remediation_planner/` contracts, deterministic scoring, planning, report writers, and CLI.
- Convert repository intelligence findings into advisory remediation items and remediation batches.
- Export optional latest, timestamped, and JSONL outputs under `.control_plane/remediation_plans/`.
- Add optional integrations:
  - Strategic Missions can convert top remediation batches into advisory mission candidates.
  - Executive Briefing can surface high-priority remediation backlog risks when report is present.
- Keep queue semantics and runtime behavior unchanged with no auto-enqueue or execution.

Phase 22: Remediation Batch Handoff Engine (RBHE).
Status: complete.

- Add `src/remediation_handoff/` contracts, deterministic package generator, codex prompt builder, report writers, and CLI.
- Convert remediation batches into implementation packages with objective, file scope, validation commands, risk notes, and human review notes.
- Export optional artifacts under `.control_plane/remediation_handoffs/`.
- Add optional integrations:
  - Strategic missions can reference generated implementation packages.
  - Executive briefing can report remediation handoff readiness when artifacts are present.
- Keep queue semantics and runtime behavior unchanged with no execution, enqueue, or enforcement.
  - Strategic Missions convert repository intelligence findings into additional mission candidates when report is present.
- Keep RIE optional and non-blocking when no report exists.
- Keep runtime/queue behavior unchanged and advisory-only.
