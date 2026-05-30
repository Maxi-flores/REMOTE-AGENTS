from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Set

from repository_intelligence.contracts import RepositoryCoverageFinding, RepositoryIntelligenceReport, new_id, utc_now, validate_repository_intelligence_report_dict


def analyze_repository_intelligence(
    inventory: Dict[str, Any],
    *,
    repository_name: str,
) -> Dict[str, Any]:
    findings: List[Dict[str, Any]] = []
    source_dirs = _as_set(inventory.get("source_directories"))
    test_files = _as_set(inventory.get("test_files"))
    docs_files = _as_set(inventory.get("documentation_files"))
    config_files = _as_set(inventory.get("config_files"))
    runtime_entrypoints = _as_set(inventory.get("runtime_entrypoints"))

    # source module coverage
    for src_dir in sorted(source_dirs):
        module = src_dir.split("/")[-1]
        has_tests = any(f"test_{module}" in Path(t).name for t in test_files)
        if not has_tests:
            findings.append(
                _finding(
                    category="testing",
                    severity="medium",
                    title=f"Source module without direct tests: {module}",
                    description=f"Module '{src_dir}' has no direct test file pattern match in tests/test_{module}*.py.",
                    path_refs=[src_dir],
                    action=f"Add targeted tests for module '{module}'.",
                )
            )
        has_docs = any(module in Path(d).stem.replace("-", "_") for d in docs_files)
        if not has_docs:
            findings.append(
                _finding(
                    category="documentation",
                    severity="low",
                    title=f"Source module without subsystem docs: {module}",
                    description=f"No docs/*.md filename appears to map directly to module '{module}'.",
                    path_refs=[src_dir],
                    action=f"Add or update docs coverage for '{module}'.",
                )
            )

    # CLI coverage
    for entry in sorted(runtime_entrypoints):
        if not entry.endswith("/cli.py"):
            continue
        module = Path(entry).parts[-2]
        has_cli_test = any(module in Path(t).name and "cli" in Path(t).name for t in test_files)
        if not has_cli_test:
            findings.append(
                _finding(
                    category="testing",
                    severity="medium",
                    title=f"CLI without matching CLI test: {module}",
                    description=f"CLI entrypoint '{entry}' has no matching tests/*cli* coverage.",
                    path_refs=[entry],
                    action=f"Add CLI tests for '{module}'.",
                )
            )

    # config contract signal
    if config_files:
        has_config_contract = any("contract" in Path(t).name and ("registry" in Path(t).name or "config" in Path(t).name) for t in test_files)
        if not has_config_contract:
            findings.append(
                _finding(
                    category="contracts",
                    severity="medium",
                    title="Config exists without clear contract test coverage",
                    description="config/*.json files exist, but no obvious config/registry contract tests were found.",
                    path_refs=sorted(config_files)[:5],
                    action="Add config contract tests for key JSON configuration files.",
                )
            )

    # runtime compatibility check presence
    if any("platform_engine.py" in e for e in runtime_entrypoints):
        has_runtime_compat = any("runtime_compat_platform_engine_path" in Path(t).stem for t in test_files)
        if not has_runtime_compat:
            findings.append(
                _finding(
                    category="runtime",
                    severity="high",
                    title="Runtime compatibility test missing for platform engine path",
                    description="Legacy/canonical platform_engine path coverage test was not detected.",
                    path_refs=sorted([e for e in runtime_entrypoints if "platform_engine.py" in e]),
                    action="Add runtime compatibility tests for legacy and canonical platform_engine paths.",
                )
            )

    # lifecycle/release/memory doc coverage signals
    docs_joined = " ".join(sorted(docs_files)).lower()
    for subsystem, severity in (("lifecycle", "medium"), ("release", "medium"), ("memory", "low")):
        if subsystem in "".join(sorted(source_dirs)).lower() and subsystem not in docs_joined:
            findings.append(
                _finding(
                    category=subsystem if subsystem in {"lifecycle", "release", "memory"} else "system",
                    severity=severity,
                    title=f"{subsystem.capitalize()} subsystem docs appear incomplete",
                    description=f"Detected source subsystem '{subsystem}' without matching docs filename hints.",
                    path_refs=[p for p in sorted(source_dirs) if subsystem in p.lower()][:3],
                    action=f"Add or update {subsystem} subsystem documentation.",
                )
            )

    opportunities = _mission_opportunities(findings)
    report = RepositoryIntelligenceReport(
        report_id=new_id("repo_intel_report"),
        generated_utc=utc_now(),
        repository_name=repository_name,
        overall_status=_overall_status(findings),
        inventory=inventory,
        findings=findings,
        suggested_mission_opportunities=opportunities,
        advisory_only=True,
        metadata={"advisory_only": True},
    ).to_dict()
    validate_repository_intelligence_report_dict(report)
    return report


def _finding(*, category: str, severity: str, title: str, description: str, path_refs: List[str], action: str) -> Dict[str, Any]:
    return RepositoryCoverageFinding(
        finding_id=new_id("repo_finding"),
        category=category,
        severity=severity,
        title=title,
        description=description,
        path_refs=path_refs,
        recommended_action=action,
        advisory_only=True,
        metadata={"advisory_only": True},
    ).to_dict()


def _mission_opportunities(findings: List[Dict[str, Any]]) -> List[str]:
    ops: List[str] = []
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        action = str(finding.get("recommended_action") or "").strip()
        if action and action not in ops:
            ops.append(action)
    return ops[:20]


def _overall_status(findings: List[Dict[str, Any]]) -> str:
    severities = {str(f.get("severity")) for f in findings if isinstance(f, dict)}
    if "critical" in severities:
        return "critical"
    if "high" in severities:
        return "degraded"
    if "medium" in severities or "low" in severities:
        return "warning"
    return "healthy"


def _as_set(value: Any) -> Set[str]:
    if not isinstance(value, list):
        return set()
    return {str(v) for v in value if isinstance(v, str)}

