# Designated Agents List (DESIGNATED_AGENTS_LIST.md)

This file assigns runtime roles to Python modules/classes and defines the
default pipeline order for the REMOTE-AGENTS autonomous office.

```json
{
  "default_pipeline": [
    "intake_specialist",
    "software_architect",
    "risk_compliance",
    "build_orchestrator"
  ],
  "agents": {
    "intake_specialist": { "module": "agents.intake_specialist", "class": "IntakeSpecialist" },
    "software_architect": { "module": "agents.software_architect", "class": "SoftwareArchitect" },
    "risk_compliance": { "module": "agents.risk_compliance", "class": "RiskCompliance" },
    "build_orchestrator": { "module": "agents.build_orchestrator", "class": "BuildOrchestrator" }
  },
  "repository_overrides": {}
}
```
