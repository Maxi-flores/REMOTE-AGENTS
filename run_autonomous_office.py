"""Main entrypoint for the REMOTE-AGENTS autonomous office runtime."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from agents.registry import AgentRegistry
from core.governance import GovernanceLogger
from core.handshake import HandshakePipeline, handshake_schemas
from core.logconf import component_logger, configure_logging
from core.orchestrator import run_sync
from core.proof_ledger import ProofLedgerManager
from core.recovery import CheckpointFormatError, CheckpointManager
from core.transaction_manager import cleanup_workspace_staging


def _read_business_case(args: argparse.Namespace) -> str:
    if args.business_case is not None:
        return str(args.business_case)
    if args.business_case_file is not None:
        path = Path(args.business_case_file)
        return path.read_text(encoding="utf-8", errors="replace")
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise SystemExit("Provide --business-case, --business-case-file, or pipe content via stdin.")


def _load_source_text(repo_root: Path) -> tuple[str, str | None]:
    """Deterministic intake sources (first match wins)."""
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the REMOTE-AGENTS autonomous office runtime.")
    parser.add_argument("--business-case", help="Freeform business case text.")
    parser.add_argument("--business-case-file", help="Path to a business case text file.")
    parser.add_argument(
        "--repo-root",
        default=str(Path.cwd()),
        help="Repository root that contains AGENT_GUIDE_LIST.md (default: CWD).",
    )
    parser.add_argument(
        "--log-dir",
        default=str(Path.cwd() / "logs"),
        help="Directory for governance logs (default: ./logs).",
    )
    parser.add_argument(
        "--legacy-intake",
        action="store_true",
        help="Run the legacy OFFICE_INTAKE/INTAKE-driven pipeline path.",
    )
    parser.add_argument(
        "--resolve-intervention",
        action="store_true",
        help="Re-validate a human-fixed checkpoint payload and resume execution.",
    )
    args = parser.parse_args(argv)

    if args.legacy_intake:
        return asyncio.run(_amain())

    repo_root = Path(args.repo_root).resolve()
    log_dir = Path(args.log_dir).resolve()
    business_case = _read_business_case(args)

    checkpoint = CheckpointManager(logs_dir=log_dir, business_case=business_case)
    proof_ledger = ProofLedgerManager(logs_dir=log_dir, execution_token=checkpoint.token)
    governance = GovernanceLogger(root=log_dir, proof_ledger=proof_ledger)
    resume = None
    try:
        resume = checkpoint.load()
    except CheckpointFormatError as exc:
        governance.emit_event({"event": "CHECKPOINT_INVALID", "error": str(exc)})
        resume = None

    # Always clear or finalize any orphaned workspace staging for this execution token.
    cleanup_workspace_staging(
        repo_root=repo_root,
        token=checkpoint.token,
        active_stage=resume.active_stage if resume is not None else None,
    )

    if resume is not None and checkpoint.requires_manual_intervention():
        governance.emit_event({"event": "INTERVENTION_REQUIRED", "active_stage": resume.active_stage})
        if not args.resolve_intervention:
            return 2
        repaired = checkpoint.resolve_intervention(schemas=handshake_schemas())
        if repaired is not None:
            resume = repaired
        cleanup_workspace_staging(repo_root=repo_root, token=checkpoint.token, active_stage=resume.active_stage)
        governance.set_state("Running")

    return run_sync(
        business_case=business_case,
        repo_root=repo_root,
        governance=governance,
        checkpoint=checkpoint,
        resume=resume,
    )


if __name__ == "__main__":
    raise SystemExit(main())
