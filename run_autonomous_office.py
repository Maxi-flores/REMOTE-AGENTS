import asyncio
import json
from pathlib import Path

from core.handshake import HandshakePipeline
from core.logconf import configure_logging, component_logger
from core.matrix_verifier import MatrixVerifier, load_governance_policy
from core.telemetry import TelemetryTracker, estimate_payload_bytes
from agents.registry import AgentRegistry


def _load_source_text(repo_root: Path) -> tuple[str, str | None, str]:
    """
    Deterministic intake sources (first match wins):
      - OFFICE_INTAKE.json: {"source_text": "...", "repository_name": "..."}
      - INTAKE.txt: raw text
    """
    intake_json = repo_root / "OFFICE_INTAKE.json"
    if intake_json.exists():
        obj = json.loads(intake_json.read_text(encoding="utf-8"))
        if isinstance(obj, dict) and isinstance(obj.get("source_text"), str):
            return obj["source_text"], obj.get("repository_name"), "OFFICE_INTAKE.json"

    intake_txt = repo_root / "INTAKE.txt"
    if intake_txt.exists():
        return intake_txt.read_text(encoding="utf-8"), None, "INTAKE.txt"

    return "Initialize autonomous office runtime core for REMOTE-AGENTS.", "REMOTE-AGENTS", "default"


async def _amain() -> int:
    repo_root = Path(__file__).resolve().parent
    logs_dir = repo_root / "logs"

    configure_logging()
    log = component_logger("OfficeRunner")

    source_text, repository_name, intake_source = _load_source_text(repo_root)
    log.info("Office intake loaded (repository=%s, bytes=%s)", repository_name, len(source_text))

    telemetry = TelemetryTracker(max_events=2048)
    policy = load_governance_policy(repo_root / "AGENT_GUIDE_LIST.md", repository_name=repository_name)
    verifier = MatrixVerifier(policy)
    await telemetry.record(
        component="OfficeRunner",
        event_type="intake_loaded",
        twin_hash="-",
        latency_ms=0.0,
        payload_bytes=estimate_payload_bytes(source_text),
        extra={"intake_source": intake_source},
    )

    registry = AgentRegistry(repo_root=repo_root, logs_dir=logs_dir)
    isa, sas, crs, boa = registry.build(repository_name=repository_name)

    pipeline = HandshakePipeline(schema_dir=repo_root / "schema", logs_dir=logs_dir)
    artifact = await pipeline.run(
        isa=isa,
        sas=sas,
        crs=crs,
        boa=boa,
        source_text=source_text,
        repository_name=repository_name,
        telemetry_tracker=telemetry,
        verifier=verifier,
    )

    print(json.dumps(artifact, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


def main() -> int:
    return asyncio.run(_amain())


if __name__ == "__main__":
    raise SystemExit(main())
