# Repository Governance MVP

Phase 7 adds repository governance contracts, health snapshots, audit records, registry import helpers, and policy evaluation metadata.

## Purpose

This phase prepares REMOTE-AGENTS and Sentient OS for enterprise repository visibility:

- governance profiles
- repository health snapshots
- audit records
- policy decision explanations
- future CI, PR governance, rollback, and Repository Center views

## Compatibility Boundary

Phase 7 is metadata and audit only.

It does not:

- replace `platform_engine.py`
- replace `.platform_queue/next_task.json`
- introduce distributed workers
- introduce cloud execution
- add a network service
- add a daemon
- mutate target repositories
- run destructive commands
- make governance enforcement mandatory at runtime

Existing runtime execution is unchanged.

## Governance Profile Contract

Profiles include:

- `repository_name`
- `repository_group`
- `repository_category`
- `status`
- `primary_agent_class`
- `twin_agent_class`
- `allowed_operations`
- `denied_operations`
- `required_checks`
- `risk_tier`
- `default_branch`
- `workspace_path`
- `deployment_targets`
- `secrets_policy`
- `network_policy`
- `write_policy`
- `approval_policy`
- `metadata`
- `created_utc`
- `updated_utc`

Allowed statuses:

- `active`
- `pending`
- `archived`
- `disabled`
- `unknown`

Allowed risk tiers:

- `low`
- `medium`
- `high`
- `critical`

## Health Snapshot Contract

Health snapshots include:

- `snapshot_id`
- `repository_name`
- `status`
- `checked_utc`
- `branch`
- `working_tree_state`
- `build_status`
- `lint_status`
- `test_status`
- `typecheck_status`
- `known_risks`
- `missing_contracts`
- `warnings`
- `errors`
- `metadata`

Allowed health statuses:

- `healthy`
- `warning`
- `degraded`
- `failing`
- `unknown`

## Audit Record Contract

Audit records include:

- `audit_id`
- `repository_name`
- `mission_id`
- `task_id`
- `actor`
- `action`
- `operation`
- `decision`
- `risk_tier`
- `reason`
- `created_utc`
- `metadata`

Allowed decisions:

- `allowed`
- `denied`
- `needs_approval`
- `needs_review`
- `unknown`

## Local Store

Governance state is stored at:

```text
.governance/repositories.json
```

Shape:

```json
{
  "schema_version": 1,
  "profiles": {},
  "health_snapshots": {},
  "audit_records": {}
}
```

Writes use atomic replacement. The store is local JSON only and does not mutate target repositories.

## Registry Import

`import_profiles_from_repositories_registry(...)` creates governance profile objects from `config/registries/repositories.json`.

The import helper:

- maps repository group, category, status, primary agent, and twin agent fields
- infers conservative risk tiers from known structural indicators
- adds default read-only allowed operations
- adds approval-oriented write, network, and deployment policies
- preserves source metadata
- does not modify the canonical registry

## Policy Evaluation

Policy helpers are advisory in Phase 7.

Default behavior:

- explicitly denied operations are denied
- `read`, `git_status`, and `git_diff` are allowed by default when not denied
- `write`, `git_commit`, `git_push`, `deploy`, `network_fetch`, and `shell_command` require approval unless future policy explicitly changes enforcement
- unknown operations return `needs_review`
- high and critical risk profiles prefer `needs_approval` for non-safe operations

Governance policies are not mandatory runtime enforcement gates yet.
