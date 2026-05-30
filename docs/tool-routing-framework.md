# MCP Tool Routing Framework MVP

Phase 5 adds a compatibility-safe MCP Tool Routing Framework MVP.

## Purpose

The router normalizes tool metadata from the canonical Phase 1 registry and the legacy platform MCP tool schema. It can resolve a tool route, explain policy implications, and format an audit record for future control-plane use.

This is metadata and policy planning only.

## Compatibility Boundary

Phase 5 does not:

- replace `platform_engine.py` tool execution
- invoke tools
- change `.platform_queue/next_task.json`
- require the new router at runtime
- add distributed workers
- add cloud execution
- add a network service
- add a daemon
- write persistent audit records

Tool invocation still happens in the legacy engine.

Future phases may connect this router to the Agent Runtime, Approval Service, Mission Engine, and Sentient OS Tool Center.

## Route Contract

Tool routes include:

- `tool_name`
- `provider`
- `implementation_status`
- `risk_tier`
- `approval_required`
- `allowed_runtime_contexts`
- `allowed_repository_groups`
- `denied_repository_groups`
- `requires_repo_boundary`
- `requires_path_safety`
- `network_access`
- `write_access`
- `audit_required`
- `metadata`

Allowed providers:

- `local_builtin`
- `mcp`
- `shell`
- `ollama`
- `codex`
- `claude_code`
- `browser`
- `external_api`
- `future_cloud`

Allowed implementation statuses:

- `active`
- `planned`
- `disabled`
- `deprecated`

Allowed risk tiers:

- `low`
- `medium`
- `high`
- `critical`

## Registry Sources

The router reads:

- canonical seed metadata from `config/registries/tools.json`
- legacy tool schemas from `config/platform_mcp_tools.json`

Either file may be missing during local experiments. Missing config resolves to an empty registry, and unknown tools resolve to a disabled high-risk fallback route.

## Policy Defaults

The Phase 5 policy helpers encode planning defaults:

- network-capable tools are denied by default unless explicitly allowed
- write-capable tools require approval
- repository-bound tools require path traversal protection
- unknown tools resolve to disabled and high risk
- diagnostic fallback should prefer read-only, no-network behavior

These are not runtime gates yet. They are planning signals for future enforcement.

## Audit Formatter

`build_tool_route_audit_record(...)` formats an audit record with:

- `audit_id`
- `tool_name`
- `provider`
- `risk_tier`
- `approval_required`
- `repository_name`
- `mission_id`
- `task_id`
- `requested_by`
- `created_utc`
- `metadata`

The formatter does not write to disk. Persistent audit storage is a later phase concern.
