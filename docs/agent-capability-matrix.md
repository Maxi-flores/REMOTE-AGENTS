# Agent Capability Matrix MVP

Phase 16 adds an advisory capability matrix foundation for scaling agent governance across repositories.

## Scope

This phase adds:

- capability profile contracts
- lifecycle state contracts
- capability profile inference from canonical registries
- repository coverage and capability gap analysis
- advisory health and SPOF detection

## Compatibility Boundary

Phase 16 does not:

- execute agents
- change runtime execution behavior
- change queue behavior
- replace `platform_engine.py`

Writes are limited to `.lifecycle/` for optional lifecycle artifacts.

