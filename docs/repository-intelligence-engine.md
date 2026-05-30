# Repository Intelligence Engine (Phase 20)

## Status

Phase 20 is complete as an advisory-only subsystem.

## Purpose

Repository Intelligence Engine (RIE) scans local repository structure and produces deterministic advisory intelligence reports for:

- source/test/doc/config/runtime coverage
- contract and CLI test alignment signals
- coverage gaps and risk areas
- suggested mission opportunities

## Safety Boundary

RIE does not:

- execute tasks
- enqueue queue payloads
- modify runtime behavior
- modify repositories
- enforce policy gates

RIE output artifacts are optional and written only under:

- `.control_plane/repository_intelligence/`

## CLI

```bash
python src/repository_intelligence/cli.py --print
python src/repository_intelligence/cli.py --export
python src/repository_intelligence/cli.py --export-jsonl
python src/repository_intelligence/cli.py --export --export-jsonl
```

## Optional Integrations

When a latest RIE report exists:

- Executive Briefing ingests high/critical repository findings.
- Strategic Mission Generation converts repository findings into additional mission candidates.

When no RIE report exists:

- existing behavior remains unchanged.

