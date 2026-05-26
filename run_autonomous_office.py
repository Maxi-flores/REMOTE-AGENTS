"""Main entrypoint for the REMOTE-AGENTS autonomous office runtime."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from core.governance import GovernanceLogger
from core.orchestrator import run_sync


def _read_business_case(args: argparse.Namespace) -> str:
    if args.business_case is not None:
        return str(args.business_case)
    if args.business_case_file is not None:
        path = Path(args.business_case_file)
        return path.read_text(encoding="utf-8", errors="replace")
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise SystemExit("Provide --business-case, --business-case-file, or pipe content via stdin.")


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
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    log_dir = Path(args.log_dir).resolve()
    business_case = _read_business_case(args)

    governance = GovernanceLogger(root=log_dir)
    return run_sync(business_case=business_case, repo_root=repo_root, governance=governance)


if __name__ == "__main__":
    raise SystemExit(main())

