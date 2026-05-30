from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict


def build_gate_trace(decision: Dict[str, Any], report: Dict[str, Any], policy: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "trace_id": decision.get("decision_id"),
        "decision": decision,
        "report_summary": {
            "report_id": report.get("report_id"),
            "readiness_score": report.get("readiness_score"),
            "readiness_status": report.get("readiness_status"),
            "finding_count": len(report.get("findings", [])) if isinstance(report.get("findings"), list) else 0,
        },
        "policy_summary": {
            "policy_id": policy.get("policy_id"),
            "minimum_readiness_score": policy.get("minimum_readiness_score"),
            "advisory_only": policy.get("advisory_only", True),
        },
        "metadata": {"advisory_only": True},
    }


def write_gate_trace(trace: Dict[str, Any], path: str | Path = ".release_reports/gate_trace.json") -> Path:
    out_path = Path(path)
    _require_release_reports_path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_name(f".{out_path.name}.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(trace, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, out_path)
    return out_path


def append_gate_trace_jsonl(trace: Dict[str, Any], path: str | Path = ".release_reports/gate_traces.jsonl") -> Path:
    out_path = Path(path)
    _require_release_reports_path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(trace, sort_keys=True))
        f.write("\n")
    return out_path


def _require_release_reports_path(path: Path) -> None:
    normalized = str(path).replace("\\", "/")
    if "/.release_reports/" not in f"/{normalized}":
        raise ValueError("path must be under .release_reports/")

