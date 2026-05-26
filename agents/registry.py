from pathlib import Path

from .boa import BuildOrchestrationAgent
from .config_loader import load_agent_guide_configs
from .crs import ComplianceRiskSpecialist
from .isa import IntakeSpecialistAgent
from .sas import SoftwareArchitectSpecialist


class AgentRegistry:
    def __init__(self, repo_root: Path, logs_dir: Path) -> None:
        self._repo_root = repo_root
        self._logs_dir = logs_dir
        self._configs = load_agent_guide_configs(repo_root / "AGENT_GUIDE_LIST.md")

    def build(self, repository_name: str | None = None) -> tuple:
        cfg = self._configs.get(repository_name or "", {})
        isa = IntakeSpecialistAgent(config=cfg)
        sas = SoftwareArchitectSpecialist(config=cfg)
        crs = ComplianceRiskSpecialist(config=cfg)
        boa = BuildOrchestrationAgent(logs_dir=self._logs_dir, config=cfg)
        return isa, sas, crs, boa
