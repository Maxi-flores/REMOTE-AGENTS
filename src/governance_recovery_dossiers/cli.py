from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence, TextIO

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from governance_recovery_dossiers.generator import generate_governance_recovery_dossier_report
from governance_recovery_dossiers.reports import (
    append_governance_recovery_dossier_report_jsonl,
    write_governance_recovery_dossier_report,
    write_timestamped_governance_recovery_dossier_report,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Governance Recovery Execution Dossiers CLI.")
    parser.add_argument("--print", action="store_true", dest="print_report")
    parser.add_argument("--export", action="store_true")
    parser.add_argument("--export-jsonl", action="store_true")
    parser.add_argument("--base-dir", default=".")
    parser.add_argument("--from-recovery-report")
    return parser


def main(argv: Sequence[str] | None = None, *, stdout: TextIO | None = None) -> int:
    args = build_parser().parse_args(argv)
    out = stdout or sys.stdout
    base_dir = Path(args.base_dir)
    report = generate_governance_recovery_dossier_report(
        base_dir=base_dir,
        recovery_report_path=args.from_recovery_report,
    )
    if args.export:
        write_governance_recovery_dossier_report(
            report,
            path=base_dir / ".control_plane" / "governance_recovery_dossiers" / "latest.json",
        )
        write_timestamped_governance_recovery_dossier_report(
            report,
            directory=base_dir / ".control_plane" / "governance_recovery_dossiers",
        )
    if args.export_jsonl:
        append_governance_recovery_dossier_report_jsonl(
            report,
            path=base_dir / ".control_plane" / "governance_recovery_dossiers" / "history.jsonl",
        )
    if args.print_report or not (args.export or args.export_jsonl):
        out.write("Governance Recovery Dossiers\n\n")
        wave_summary = report.get("wave_summary") if isinstance(report.get("wave_summary"), list) else []
        for wave in wave_summary:
            if not isinstance(wave, dict):
                continue
            out.write(
                f"{wave.get('wave_id', 'wave_unknown')} | dossiers={wave.get('dossier_count', 0)} | "
                f"high={wave.get('high_risk_count', 0)} | critical={wave.get('critical_risk_count', 0)}\n"
            )
        out.write("\n")
        out.write(json.dumps(report, indent=2, sort_keys=True))
        out.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

