"""Agent role modules for the autonomous office."""

from .boa import BuildOrchestrationAgent
from .build_orchestrator import BuildOrchestrator
from .crs import ComplianceRiskSpecialist
from .intake_specialist import IntakeSpecialist
from .isa import IntakeSpecialistAgent
from .registry import AgentRegistry
from .risk_compliance import RiskCompliance
from .sas import SoftwareArchitectSpecialist
from .software_architect import SoftwareArchitect

__all__ = [
    "AgentRegistry",
    "IntakeSpecialistAgent",
    "SoftwareArchitectSpecialist",
    "ComplianceRiskSpecialist",
    "BuildOrchestrationAgent",
    "IntakeSpecialist",
    "SoftwareArchitect",
    "RiskCompliance",
    "BuildOrchestrator",
]
