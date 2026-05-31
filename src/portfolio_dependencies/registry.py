from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from portfolio_dependencies.contracts import RepositoryDependency, validate_repository_dependency_dict


def default_dependencies_path(base_dir: str | Path = ".") -> Path:
    return Path(base_dir) / ".config" / "portfolio" / "dependencies.json"


def load_dependency_registry(path: str | Path | None = None, *, base_dir: str | Path = ".") -> List[Dict[str, Any]]:
    p = Path(path) if path else default_dependencies_path(base_dir)
    payload = _load_json(p)
    repos = payload.get("repositories")
    if not isinstance(repos, list):
        return []
    out: List[Dict[str, Any]] = []
    for item in repos:
        if not isinstance(item, dict):
            continue
        record = RepositoryDependency(
            repository_id=str(item.get("repository_id") or "unknown"),
            depends_on=[str(v) for v in (item.get("depends_on") if isinstance(item.get("depends_on"), list) else []) if str(v).strip()],
            metadata=dict(item.get("metadata") or {}),
        ).to_dict()
        validate_repository_dependency_dict(record)
        out.append(record)
    return out


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}

