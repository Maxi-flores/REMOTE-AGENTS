from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from portfolio_orchestration.contracts import (
    PortfolioRepository,
    validate_portfolio_repository_dict,
)


def default_registry_path(base_dir: str | Path = ".") -> Path:
    root = Path(base_dir)
    return root / ".config" / "portfolio" / "portfolio_registry.json"


def load_portfolio_registry(path: str | Path | None = None, *, base_dir: str | Path = ".") -> List[Dict[str, Any]]:
    registry_path = Path(path) if path else default_registry_path(base_dir)
    payload = _load_json(registry_path)
    repos = payload.get("repositories")
    if not isinstance(repos, list):
        return []
    out: List[Dict[str, Any]] = []
    for record in repos:
        if not isinstance(record, dict):
            continue
        normalized = PortfolioRepository(
            repository_id=str(record.get("repository_id") or record.get("repository_name") or "unknown"),
            repository_name=str(record.get("repository_name") or "unknown"),
            repository_path=str(record.get("repository_path") or "."),
            repository_type=str(record.get("repository_type") or "unknown"),
            enabled=bool(record.get("enabled", True)),
            metadata=dict(record.get("metadata") or {}),
        ).to_dict()
        validate_portfolio_repository_dict(normalized)
        out.append(normalized)
    return out


def list_enabled_repositories(path: str | Path | None = None, *, base_dir: str | Path = ".") -> List[Dict[str, Any]]:
    return [r for r in load_portfolio_registry(path, base_dir=base_dir) if bool(r.get("enabled"))]


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}

