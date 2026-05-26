import asyncio
import json
from pathlib import Path

from core.handshake import HandshakePipeline
from core.logconf import configure_logging, component_logger
from agents.registry import AgentRegistry


def _load_source_text(repo_root: Path) -> tuple[str, str | None]:
    """
    Deterministic intake sources (first match wins):
      - OFFICE_INTAKE.json: {"source_text": "...", "repository_name": "..."}
      - INTAKE.txt: raw text
    """
    intake_json = repo_root / "OFFICE_INTAKE.json"
    if intake_json.exists():
        obj = json.loads(intake_json.read_text(encoding="utf-8"))
        if isinstance(obj, dict) and isinstance(obj.get("source_text"), str):
            return obj["source_text"], obj.get("repository_name")

    intake_txt = repo_root / "INTAKE.txt"
    if intake_txt.exists():
        return intake_txt.read_text(encoding="utf-8"), None

    return "Initialize autonomous office runtime core for REMOTE-AGENTS.", "REMOTE-AGENTS"


async def _amain() -> int:
    repo_root = Path(__file__).resolve().parent
    logs_dir = repo_root / "logs"

    configure_logging()
    log = component_logger("OfficeRunner")

    source_text, repository_name = _load_source_text(repo_root)
    log.info("Office intake loaded (repository=%s, bytes=%s)", repository_name, len(source_text))

    registry = AgentRegistry(repo_root=repo_root, logs_dir=logs_dir)
    isa, sas, crs, boa = registry.build(repository_name=repository_name)

    pipeline = HandshakePipeline(schema_dir=repo_root / "schema", logs_dir=logs_dir)
    artifact = await pipeline.run(isa=isa, sas=sas, crs=crs, boa=boa, source_text=source_text, repository_name=repository_name)

    print(json.dumps(artifact, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


def main() -> int:
    return asyncio.run(_amain())


if __name__ == "__main__":
    raise SystemExit(main())
