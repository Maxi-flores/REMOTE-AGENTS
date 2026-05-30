# Registry Architecture

Phase 1 introduces canonical structured registries for the future Agent Operating System without changing current runtime behavior.

## Compatibility Boundary

The live runtime still loads `config/agent_registry.json` through `src/routers/repo_governance_router.py`.

The new files under `config/registries/` are seed registries for future phases. They are intentionally data-only in Phase 1:
- no new runtime loader
- no queue changes
- no Mission Engine
- no distributed workers
- no cloud execution

## Canonical Registry Files

### `config/registries/repositories.json`

Seed source: `AGENT_GUIDE_LIST.md` and `config/agent_registry.json`.

Contains:
- repository name
- repository group/category
- detected class
- primary agent class
- twin agent class
- status
- core objective
- known structural health indicators

Purpose:
- Make repository governance data machine-readable.
- Preserve the guide concepts while avoiding a runtime migration in Phase 1.

### `config/registries/agents.json`

Seed source: `config/agent_registry.json` and the crew persona blueprint in `AGENT_GUIDE_LIST.md`.

Contains:
- agent class id
- display name
- role
- crew family
- primary/twin type
- default constraints
- recommended use cases

Purpose:
- Define a future capability registry surface.
- Let repositories point to canonical agent class ids.

### `config/registries/tools.json`

Seed source: `config/platform_mcp_tools.json`.

Contains:
- tool name
- description
- risk tier
- approval requirements
- allowed runtime context
- current implementation status

Purpose:
- Provide governance metadata around the existing local MCP-style tool schema.
- Keep the actual runtime schema in `config/platform_mcp_tools.json` for compatibility.

### `config/registries/models.json`

Seed source: `Codex.md` and current platform defaults.

Contains:
- `qwen2.5-coder:3b`
- optional router/gatekeeper models from `Codex.md`
- default thread budget
- max recommended memory footprint
- intended use

Purpose:
- Document model routing intent without introducing a model router yet.

### `config/registries/policies.json`

Seed source: current runtime behavior.

Contains:
- write approval required
- network default deny
- path traversal protection
- max loop count of 5
- local-first execution
- default diagnostic fallback behavior

Purpose:
- Make current governance assumptions explicit for later policy-engine work.

## Validation

`tests/test_registry_contracts.py` verifies:
- all canonical registry JSON files parse
- repository primary/twin agent references exist in `agents.json` unless a repo is explicitly pending without an assignment
- legacy `config/agent_registry.json` still routes through the existing router
- `config/platform_mcp_tools.json` remains parseable
- canonical tool names match the current MCP tool schema

## Future Phase Notes

Phase 1 does not decide the final schema version for Sentient OS. These files are intentionally conservative seed registries. Later phases can add richer fields such as ownership, risk tier inheritance, eval scores, tool trust policies, lifecycle state, and migration tooling.
