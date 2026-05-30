from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from control_plane.orchestrator_contracts import (
    ControlPlaneOrchestrationReport,
    ControlPlaneOrchestrationRequest,
    ControlPlaneOrchestrationStageResult,
    new_id,
    utc_now,
    validate_orchestration_report_dict,
    validate_orchestration_request_dict,
)


STAGE_ORDER = [
    "mission",
    "scheduler",
    "tool_router",
    "governance",
    "memory_graph",
    "release_readiness",
    "release_gates",
    "release_center",
    "lifecycle",
    "snapshot",
    "sentient_ui",
]


def create_orchestration_request(
    *,
    trigger_source: str = "manual",
    mission_id: str | None = None,
    task_ids: List[str] | None = None,
    target_repositories: List[str] | None = None,
) -> Dict[str, Any]:
    request = ControlPlaneOrchestrationRequest(
        orchestration_id=new_id("cpo"),
        trigger_source=trigger_source if trigger_source else "unknown",
        mission_id=mission_id,
        task_ids=list(task_ids or []),
        target_repositories=list(target_repositories or []),
        requested_utc=utc_now(),
        advisory_only=True,
        metadata={"advisory_only": True},
    ).to_dict()
    validate_orchestration_request_dict(request)
    return request


def run_orchestration(
    request: Dict[str, Any],
    *,
    base_dir: str | Path = ".",
) -> Dict[str, Any]:
    validate_orchestration_request_dict(request)
    root = Path(base_dir)
    stage_results: List[Dict[str, Any]] = []
    for stage_name in STAGE_ORDER:
        stage_results.append(_run_stage(stage_name, root))
    pipeline_status = _derive_pipeline_status(stage_results)
    findings = _cross_stage_findings(stage_results)
    actions = _recommended_actions(stage_results)
    report = ControlPlaneOrchestrationReport(
        report_id=new_id("cpo_report"),
        orchestration_id=str(request["orchestration_id"]),
        generated_utc=utc_now(),
        pipeline_status=pipeline_status,
        stage_results=stage_results,
        cross_stage_findings=findings,
        recommended_next_actions=actions,
        advisory_only=True,
        metadata={
            "advisory_only": True,
            "base_dir": str(root),
            "stage_order": list(STAGE_ORDER),
            "runtime_unchanged": True,
        },
    ).to_dict()
    validate_orchestration_report_dict(report)
    return report


def _run_stage(stage_name: str, base_dir: Path) -> Dict[str, Any]:
    stage_map = {
        "mission": [base_dir / ".missions"],
        "scheduler": [base_dir / ".scheduler" / "state.json"],
        "tool_router": [base_dir / "config" / "registries" / "tools.json", base_dir / "config" / "platform_mcp_tools.json"],
        "governance": [base_dir / ".governance" / "repositories.json"],
        "memory_graph": [base_dir / ".memory" / "graph.json"],
        "release_readiness": [base_dir / ".release_reports" / "release_readiness.json"],
        "release_gates": [base_dir / ".release_reports" / "gate_trace.json"],
        "release_center": [base_dir / ".release_reports" / "release_timeline.json"],
        "lifecycle": [base_dir / ".lifecycle" / "agents.json"],
        "snapshot": [base_dir / ".control_plane" / "snapshot.json"],
        "sentient_ui": [base_dir / ".sentient_ui" / "view_model.json"],
    }
    inputs = stage_map.get(stage_name, [])
    existing = [p for p in inputs if p.exists()]
    missing = [p for p in inputs if not p.exists()]
    warnings: List[str] = []
    blockers: List[str] = []
    summary: Dict[str, Any] = {"existing_inputs": len(existing), "expected_inputs": len(inputs)}
    output_refs: List[str] = []
    status = "ok"

    if not inputs:
        status = "unknown"
        warnings.append("No configured inputs for stage")
    elif not existing:
        status = "not_run"
        warnings.append("Required advisory inputs missing")
    elif missing:
        status = "warning"
        warnings.append("Partial advisory inputs available")
    else:
        status = "ok"

    # lightweight read sanity check for JSON artifacts
    parse_failures = 0
    for path in existing:
        if path.is_dir():
            output_refs.append(str(path))
            continue
        if path.suffix.lower() in {".json", ".jsonl"}:
            try:
                if path.suffix.lower() == ".json":
                    json.loads(path.read_text(encoding="utf-8"))
                else:
                    # quick sample of first lines
                    with path.open("r", encoding="utf-8") as handle:
                        for idx, line in enumerate(handle):
                            if idx > 4:
                                break
                            text = line.strip()
                            if text:
                                json.loads(text)
            except Exception:
                parse_failures += 1
        output_refs.append(str(path))

    if parse_failures > 0:
        warnings.append(f"{parse_failures} input artifact(s) could not be parsed")
        if status == "ok":
            status = "warning"
        summary["parse_failures"] = parse_failures

    stage = ControlPlaneOrchestrationStageResult(
        stage_name=stage_name,
        status=status,
        input_refs=[str(p) for p in inputs],
        output_refs=output_refs,
        warnings=warnings,
        blockers=blockers,
        summary=summary,
        completed_utc=utc_now(),
        advisory_only=True,
        metadata={"advisory_only": True},
    ).to_dict()
    return stage


def _derive_pipeline_status(stage_results: List[Dict[str, Any]]) -> str:
    statuses = {str(stage.get("status")) for stage in stage_results if isinstance(stage, dict)}
    if "error" in statuses:
        return "error"
    if "blocked" in statuses:
        return "blocked"
    if "warning" in statuses:
        return "warning"
    if "unknown" in statuses and len(statuses) == 1:
        return "unknown"
    if "not_run" in statuses and len(statuses) == 1:
        return "warning"
    if "ok" in statuses:
        return "ok"
    return "unknown"


def _cross_stage_findings(stage_results: List[Dict[str, Any]]) -> List[str]:
    findings: List[str] = []
    for stage in stage_results:
        if not isinstance(stage, dict):
            continue
        name = str(stage.get("stage_name", "unknown"))
        status = str(stage.get("status", "unknown"))
        if status in {"warning", "not_run", "blocked", "error", "unknown"}:
            findings.append(f"{name}:{status}")
    return findings


def _recommended_actions(stage_results: List[Dict[str, Any]]) -> List[str]:
    actions: List[str] = []
    for stage in stage_results:
        if not isinstance(stage, dict):
            continue
        name = str(stage.get("stage_name", "unknown"))
        status = str(stage.get("status", "unknown"))
        if status == "not_run":
            actions.append(f"Generate missing advisory artifacts for stage '{name}'.")
        elif status == "warning":
            actions.append(f"Review partial or malformed inputs for stage '{name}'.")
        elif status in {"blocked", "error"}:
            actions.append(f"Investigate blocking issues in stage '{name}'.")
    if not actions:
        actions.append("No action required; advisory orchestration pipeline is healthy.")
    return actions

