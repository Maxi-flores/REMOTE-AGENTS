from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from portfolio_bootstrap.contracts import (
    PortfolioBootstrapReport,
    RepositoryOnboardingRecord,
    new_id,
    utc_now,
    validate_portfolio_bootstrap_report_dict,
)
from portfolio_bootstrap.discovery import discover_portfolio_repositories


def generate_portfolio_bootstrap_report(*, base_dir: str | Path = ".", registry_path: str | Path | None = None) -> Dict[str, Any]:
    discovered = discover_portfolio_repositories(base_dir=base_dir, registry_path=registry_path)
    repositories: List[Dict[str, Any]] = []
    onboarding_records: List[Dict[str, Any]] = []
    recommendations: List[str] = []

    for item in discovered:
        repo = item.get("repository") if isinstance(item.get("repository"), dict) else {}
        exists = bool(item.get("exists"))
        structure = item.get("structure") if isinstance(item.get("structure"), dict) else {}
        artifacts = item.get("artifacts") if isinstance(item.get("artifacts"), dict) else {}

        repository_id = str(repo.get("repository_id") or repo.get("repository_name") or "unknown")
        repository_name = str(repo.get("repository_name") or repository_id)
        repository_path = str(item.get("resolved_path") or repo.get("repository_path") or ".")

        artifact_status = _artifact_status(artifacts, exists)
        readiness = _readiness_estimate(structure, artifacts, exists)
        onboarding_state = _onboarding_state(exists, artifact_status, readiness)

        record = RepositoryOnboardingRecord(
            repository_id=repository_id,
            repository_name=repository_name,
            repository_path=repository_path,
            discovered=exists,
            artifact_status=artifact_status,
            readiness_estimate=readiness,
            onboarding_state=onboarding_state,
            metadata={
                "structure_presence": structure,
                "advisory_artifact_presence": artifacts,
                "readiness_formula": "readme=15 docs=15 src=25 tests=20 advisory_artifacts=25",
            },
        ).to_dict()
        onboarding_records.append(record)
        repositories.append(repo)
        recommendations.extend(_recommendations_for_record(record))

    summary = _readiness_summary(onboarding_records)
    report = PortfolioBootstrapReport(
        report_id=new_id("portfolio_bootstrap_report"),
        generated_utc=utc_now(),
        repositories=repositories,
        onboarding_records=onboarding_records,
        readiness_summary=summary,
        recommendations=_dedupe(recommendations),
        advisory_only=True,
        metadata={
            "advisory_only": True,
            "runtime_unchanged": True,
            "queue_mutation": False,
            "source_registry": str(registry_path) if registry_path else ".config/portfolio/portfolio_registry.json",
        },
    ).to_dict()
    validate_portfolio_bootstrap_report_dict(report)
    return report


def _artifact_status(artifacts: Dict[str, Any], discovered: bool) -> str:
    if not discovered:
        return "unknown"
    keys = ("repository_intelligence", "work_queue", "execution_dossiers")
    present = sum(1 for key in keys if bool(artifacts.get(key)))
    if present == 0:
        return "none"
    if present == len(keys):
        return "complete"
    return "partial"


def _readiness_estimate(structure: Dict[str, Any], artifacts: Dict[str, Any], discovered: bool) -> int:
    if not discovered:
        return 0
    score = 0
    if bool(structure.get("readme")):
        score += 15
    if bool(structure.get("docs")):
        score += 15
    if bool(structure.get("src")):
        score += 25
    if bool(structure.get("tests")):
        score += 20
    artifact_keys = ("repository_intelligence", "work_queue", "execution_dossiers")
    present = sum(1 for key in artifact_keys if bool(artifacts.get(key)))
    score += int((present / len(artifact_keys)) * 25)
    return max(0, min(100, score))


def _onboarding_state(discovered: bool, artifact_status: str, readiness_estimate: int) -> str:
    if not discovered:
        return "registered"
    if artifact_status == "complete" and readiness_estimate >= 75:
        return "onboarded"
    if readiness_estimate >= 50 or artifact_status == "partial":
        return "assessed"
    return "discovered"


def _recommendations_for_record(record: Dict[str, Any]) -> List[str]:
    repo_name = str(record.get("repository_name") or record.get("repository_id") or "repository")
    recommendations: List[str] = []
    if str(record.get("artifact_status") or "") == "none":
        recommendations.append(f"Add advisory artifacts for {repo_name}")
    elif str(record.get("artifact_status") or "") == "partial":
        recommendations.append(f"Complete advisory artifact coverage for {repo_name}")
    if int(record.get("readiness_estimate") or 0) < 50:
        recommendations.append(f"Generate repository intelligence for {repo_name}")
    if str(record.get("onboarding_state") or "") != "onboarded":
        recommendations.append(f"Onboard {repo_name} into portfolio governance")
    return recommendations


def _readiness_summary(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not records:
        return {"repository_count": 0, "average_readiness_estimate": 0, "artifact_status_counts": {}, "onboarding_state_counts": {}}
    avg = int(sum(int(r.get("readiness_estimate") or 0) for r in records) / len(records))
    artifact_counts: Dict[str, int] = {}
    onboarding_counts: Dict[str, int] = {}
    for record in records:
        art = str(record.get("artifact_status") or "unknown")
        state = str(record.get("onboarding_state") or "discovered")
        artifact_counts[art] = artifact_counts.get(art, 0) + 1
        onboarding_counts[state] = onboarding_counts.get(state, 0) + 1
    return {
        "repository_count": len(records),
        "average_readiness_estimate": avg,
        "artifact_status_counts": artifact_counts,
        "onboarding_state_counts": onboarding_counts,
    }


def _dedupe(items: List[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for item in items:
        value = str(item).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out

