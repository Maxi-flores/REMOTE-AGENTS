# Runtime Contracts

REMOTE-AGENTS currently runs as a local-first, single-worker runtime. These contracts describe the behavior that Phase 0 preserves.

## Queue Payload: `.platform_queue/next_task.json`

The worker watches for one JSON task file at `.platform_queue/next_task.json`.

Required field:
- `instruction`: string. Freeform task instruction for the local agent loop.

Optional fields:
- `task_id`: string. If omitted, the worker falls back to the payload id or file name depending on the enqueue path.
- `id`: string. Backward-compatible task id fallback.
- `target_repository`: string. Activates repository governance routing through `config/agent_registry.json`.
- `target_repositories`: string array. The router currently uses the first repository as a compatibility fallback.
- `priority`: integer. Used by the gateway/dispatcher buffer, not by the single on-disk worker file itself.
- `enqueued_utc`: string. Informational timestamp.
- `source`: string. Informational source label.

Example:

```json
{
  "instruction": "Update Vite proxy config to point to the new API port.",
  "target_repository": "ConceptSHOP",
  "priority": 2
}
```

Current behavior:
- The worker processes only one disk task at a time.
- Successful tasks remove `next_task.json`.
- Failed tasks are archived under `.platform_queue/failed/`.
- Unknown or missing repositories fall back to the default diagnostic profile.

## Processing Lock: `.platform_queue/processing.lock`

The worker creates `.platform_queue/processing.lock` before task execution using exclusive file creation.

Lock fields include:
- `task_id`
- `pid`
- `started_utc`
- `target_repository`
- `primary_agent_class`
- `twin_agent_class`
- `num_thread`

Current behavior:
- If the lock exists, other worker instances wait.
- Locks older than 15 minutes are considered stale.
- Stale locks are pruned on boot when possible.
- `/health` reports `Error-Locked` when the runtime appears stuck behind a stale lock that cannot be pruned.

## Failed Payloads: `.platform_queue/failed/`

Failed task payloads are moved to `.platform_queue/failed/` with a timestamp and task id in the filename.

Failures are also appended to `.logs/errors.json` with:
- timestamp
- task id
- loop count
- inferred error type
- last known error
- compact prompt/context snapshot

## Gateway: `POST /api/v1/trigger`

The async gateway accepts JSON task triggers and buffers them in memory until the single disk task slot is available.

Request body:

```json
{
  "instruction": "string",
  "priority": 0,
  "target_repository": "ConceptSHOP"
}
```

Rules:
- `instruction` is required and must be a non-empty string.
- `priority` is optional and must be an integer.
- `target_repository` is optional.
- Request body size is capped at 512 KiB.

Response:
- `202` with `{ "ok": true, "task_id": "..." }` when accepted.
- `400` for invalid payloads.

## Gateway: `GET /health`

Returns a JSON health snapshot for the local runtime.

Key fields:
- `state`: `Idle`, `Processing`, or `Error-Locked`.
- `buffered`: count of in-memory buffered gateway tasks.
- `disk_task_present`: whether `.platform_queue/next_task.json` exists.
- `processing_lock_present`: whether `.platform_queue/processing.lock` exists.
- `processing_lock_age_s`
- `processing_lock_details`
- `resources`: best-effort memory telemetry.
- `workspace`: repository existence/readability/writability snapshot.
- `consensus`: twin review counters.
- `semantic_memory`: memory counts by repository.

## Gateway: `GET /ws/events`

Upgrades to a WebSocket connection. Each text frame must contain the same JSON shape accepted by `POST /api/v1/trigger`.

Current behavior:
- Valid frames enqueue buffered tasks and receive `{ "ok": true, "task_id": "..." }`.
- Invalid frames close the connection.
- Fragmented frames are not supported.

## Agent Registry Contract: `config/agent_registry.json`

Top-level fields:
- `schema_version`: registry schema version.
- `description`: human-readable registry description.
- `default_profile`: fallback agent profile.
- `groups`: repository groupings for operator context.
- `repositories`: per-repository routing profiles.

Profile fields:
- `primary_agent_class`: string.
- `twin_agent_class`: string.
- `execution_constraints`: object.

Common execution constraints:
- `num_thread`: integer. Local Ollama thread target.
- `quantization_preference`: string. Informational model preference.
- `max_context_chars`: integer. Prompt history cap.
- `execute_isolated_task_readonly`: boolean.
- `execute_isolated_task_no_network`: boolean.
- `allowed_path_prefixes`: string array.
- `deny_path_prefixes`: string array.
- `allowed_write_path_prefixes`: string array.
- `deny_write_path_prefixes`: string array.

Routing behavior:
- Known repositories use their profile.
- Unknown, missing, disabled, or incomplete profiles use `default_profile`.
- Default profile execution is diagnostic and blocks writes/network by default.

## MCP Tool Schema: `config/platform_mcp_tools.json`

The platform exposes a local tool schema to the on-device model.

Current tools:
- `workspace_file_router`: read/write repo-relative files. Writes require twin approval.
- `execute_isolated_task`: run a short Python snippet in a best-effort sandbox. Requires twin approval.
- `network_data_fetch`: HTTP fetch. Disabled in the default diagnostic profile.
- `graphics_validate_transform_math`: validate 3D transform payloads.
- `graphics_parse_matrix4`: parse a 4x4 matrix into finite floats.
- `trace_asset_compilation`: run an allowlisted local compile command and return structured output.

Tool calls are routed by `PlatformAgentEngine.execute_tool`.

## Twin Consensus Approval Flow

For side-effecting operations, the primary agent proposes an action and the configured twin agent audits it.

Approval is required for:
- `workspace_file_router` writes.
- `execute_isolated_task`.
- failed `trace_asset_compilation` feedback enrichment uses twin review for actionable explanation.

Flow:
- The primary model emits a JSON decision with `tool_to_call` and `arguments`.
- The engine calls `verify_with_twin_agent`.
- Python snippets and Python file writes receive a syntax check before model audit.
- The twin must return strict JSON: `{ "approved": true|false, "feedback": "..." }`.
- Rejections are fed back into the loop as `Twin Rejection`.
- Repeated rejection until max loops causes a failed payload archive.
- Consensus counters are written to `.logs/consensus_metrics.json`.
