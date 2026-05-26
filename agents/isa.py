from .base import AgentBase
from core.hashutil import fnv1a_32


class IntakeSpecialistAgent(AgentBase):
    def __init__(self, config: dict | None = None) -> None:
        super().__init__("ISA", config=config)

    def ingest(self, source_text: str, repository_name: str | None = None) -> dict:
        requirements = self._extract_requirements(source_text)
        if not requirements:
            requirements = ["Establish autonomous office intake"]
        request_id = fnv1a_32(source_text.strip() or "empty")

        constraints: dict = {"standard_library_only": ["json", "pathlib", "asyncio", "logging"]}
        if repository_name:
            constraints["repository_name"] = repository_name
        if self.config:
            constraints["agent_guide_config"] = self.config

        return {
            "origin_agent": "ISA",
            "target_agent": "SAS",
            "protocol": "Deterministic JSON Packet",
            "payload": {
                "request_id": request_id,
                "source_text": source_text,
                "requirements": requirements,
                "constraints": constraints,
            },
        }

    def _extract_requirements(self, text: str) -> list[str]:
        reqs: list[str] = []
        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                continue
            if line.startswith(("-", "*", "•")):
                cand = line[1:].strip()
                if cand:
                    reqs.append(cand)
                continue
            lowered = line.lower()
            if lowered.startswith(("must ", "should ", "need ", "requires ")):
                reqs.append(line)
        if not reqs:
            for raw in text.splitlines():
                line = raw.strip()
                if line:
                    reqs.append(line)
                if len(reqs) >= 3:
                    break
        return [r for r in reqs if isinstance(r, str) and r.strip()]
