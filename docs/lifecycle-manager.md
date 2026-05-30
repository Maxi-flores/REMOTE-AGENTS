# Lifecycle Manager MVP

Phase 16 adds an advisory lifecycle manager baseline.

## Scope

This phase provides:

- local lifecycle store at `.lifecycle/agents.json`
- capability profile upsert/read/list
- lifecycle state register/read/update/list
- lifecycle event append
- advisory health summaries and repository coverage checks

## Notes

- Advisory only
- No agent execution
- No queue mutation
- No runtime behavior replacement

It prepares future Sentient OS Agent Center, Capability Matrix, and Lifecycle Manager views.

