import json
from pathlib import Path

from .base import AgentBase
from core.exceptions import PipelineHaltException


class BuildOrchestrationAgent(AgentBase):
    def __init__(self, logs_dir: Path, config: dict | None = None) -> None:
        super().__init__("BOA", config=config)
        self._logs_dir = logs_dir

    def build(self, crs_packet: dict, telemetry: list[dict] | None = None) -> dict:
        clearance = crs_packet.get("clearance") or {}
        if not clearance.get("build_ready", False):
            raise PipelineHaltException("CRS did not authorize build (build_ready=false)")
        if clearance.get("risk_level") in ("critical",):
            raise PipelineHaltException("CRS risk_level=critical blocks build")

        self._logs_dir.mkdir(parents=True, exist_ok=True)
        artifact = {
            "artifact_type": "REMOTE-AGENTS Autonomous Office Build Artifact",
            "status": "built",
            "telemetry": telemetry or [],
            "clearance": crs_packet,
        }
        path = self._logs_dir / "BUILD_ARTIFACT.json"
        path.write_text(json.dumps(artifact, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
        artifact["artifact_path"] = str(path)
        return artifact
