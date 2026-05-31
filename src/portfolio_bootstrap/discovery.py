from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from portfolio_orchestration.registry import load_portfolio_registry


def discover_portfolio_repositories(*, base_dir: str | Path = ".", registry_path: str | Path | None = None) -> List[Dict[str, Any]]:
    root = Path(base_dir)
    repositories = load_portfolio_registry(registry_path, base_dir=root)
    out: List[Dict[str, Any]] = []
    for repo in repositories:
        if not isinstance(repo, dict):
            continue
        repo_path = _resolve_repo_path(root, str(repo.get("repository_path") or "."))
        out.append(
            {
                "repository": repo,
                "resolved_path": str(repo_path),
                "exists": repo_path.exists(),
                "structure": inspect_repository_structure(repo_path),
                "artifacts": inspect_repository_artifacts(repo_path),
            }
        )
    return out


def inspect_repository_structure(repo_path: Path) -> Dict[str, bool]:
    return {
        "readme": (repo_path / "README.md").exists(),
        "docs": (repo_path / "docs").exists(),
        "src": (repo_path / "src").exists(),
        "tests": (repo_path / "tests").exists(),
    }


def inspect_repository_artifacts(repo_path: Path) -> Dict[str, bool]:
    cp = repo_path / ".control_plane"
    return {
        "control_plane_root": cp.exists(),
        "repository_intelligence": (cp / "repository_intelligence").exists(),
        "work_queue": (cp / "work_queue").exists(),
        "execution_dossiers": (cp / "execution_dossiers").exists(),
    }


def _resolve_repo_path(base_dir: Path, configured: str) -> Path:
    path = Path(configured)
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()

