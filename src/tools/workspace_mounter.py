from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable


_THIS_REPO_ROOT = Path(__file__).resolve().parents[2]


def _infer_default_workspace_base_dir() -> Path:
    """Infer the directory that contains multiple checked-out repositories.

    Common layouts:
      - GitHub Actions: <base>/<repo>/<repo>
      - Local dev:      <base>/<repo>
    """

    env = os.environ.get("PLATFORM_WORKSPACE_BASE_DIR", "").strip()
    if env:
        return Path(env).expanduser().resolve()

    # GitHub Actions layout heuristic: /.../work/<repo>/<repo>
    parent = _THIS_REPO_ROOT.parent
    if parent.name == _THIS_REPO_ROOT.name and parent.parent.exists():
        return parent.parent.resolve()

    # Local layout heuristic: /.../<base>/<repo>
    return parent.resolve()


def workspace_base_dir() -> Path:
    return _infer_default_workspace_base_dir()


def resolve_repo_root(target_repo: str | None) -> Path:
    """Resolve the local absolute path to a repository root directory."""

    if target_repo is None:
        return _THIS_REPO_ROOT

    if not isinstance(target_repo, str) or not target_repo.strip():
        raise ValueError("target_repo must be a non-empty string")

    target_repo = target_repo.strip()
    if target_repo == _THIS_REPO_ROOT.name:
        return _THIS_REPO_ROOT

    base = workspace_base_dir()
    candidates = [
        (base / target_repo / target_repo).resolve(),
        (base / target_repo).resolve(),
    ]
    for candidate in candidates:
        try:
            if candidate.exists() and candidate.is_dir():
                return candidate
        except OSError:
            continue

    raise FileNotFoundError(f"Repository directory not found for target_repo={target_repo!r} under {base}")


def resolve_secure_path(target_repo: str, relative_path: str) -> str:
    """Returns verified absolute path inside the targeted repository directory.

    Raises PermissionError if the path escapes the repository boundary or if an
    absolute path is supplied.
    """

    if not isinstance(relative_path, str) or not relative_path.strip():
        raise ValueError("relative_path must be a non-empty string")

    repo_root = resolve_repo_root(target_repo)
    rel = Path(relative_path)
    if rel.is_absolute():
        raise PermissionError("Absolute paths are forbidden; use a repo-relative path")

    abs_path = (repo_root / rel).resolve()

    # Explicit traversal defense using os.path.commonpath.
    repo_s = os.path.normcase(os.fspath(repo_root))
    abs_s = os.path.normcase(os.fspath(abs_path))
    common = os.path.commonpath([repo_s, abs_s])
    if common != repo_s:
        raise PermissionError(f"Path escapes repository boundary: {relative_path!r}")

    return os.fspath(abs_path)


def _load_agent_registry(registry_path: Path) -> dict[str, Any]:
    try:
        raw = registry_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    try:
        obj = json.loads(raw)
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def registry_repo_names(*, registry_path: str | Path = "config/agent_registry.json") -> list[str]:
    p = Path(registry_path)
    reg = _load_agent_registry(p)
    repos = reg.get("repositories")
    if isinstance(repos, dict):
        out = [k for k in repos.keys() if isinstance(k, str) and k.strip()]
        out.sort(key=str.casefold)
        return out
    return []


def workspace_dir_health(
    *,
    repo_names: Iterable[str] | None = None,
    base_dir: str | Path | None = None,
    registry_path: str | Path = "config/agent_registry.json",
) -> dict[str, Any]:
    """Health snapshot for multi-repo workspaces.

    Returns a JSON-serializable dict keyed by repo name with existence/access info.
    """

    base = Path(base_dir).expanduser().resolve() if base_dir is not None else workspace_base_dir()
    names = list(repo_names) if repo_names is not None else registry_repo_names(registry_path=registry_path)
    names = [n.strip() for n in names if isinstance(n, str) and n.strip()]
    names.sort(key=str.casefold)

    out: dict[str, Any] = {"base_dir": os.fspath(base), "repos": {}}
    for name in names:
        status: dict[str, Any] = {}
        try:
            root = resolve_repo_root(name)
            status["path"] = os.fspath(root)
            status["exists"] = True
            status["is_dir"] = root.is_dir()
            status["readable"] = os.access(root, os.R_OK)
            status["writable"] = os.access(root, os.W_OK)
        except FileNotFoundError:
            # Compute where we expected it to be, so diagnostics are actionable.
            status["path"] = os.fspath((base / name / name).resolve())
            status["exists"] = False
            status["is_dir"] = False
            status["readable"] = False
            status["writable"] = False
            status["error"] = "missing"
        except PermissionError as exc:
            status["exists"] = None
            status["is_dir"] = None
            status["readable"] = None
            status["writable"] = None
            status["error"] = f"permission_error: {exc}"
        except OSError as exc:
            status["exists"] = None
            status["is_dir"] = None
            status["readable"] = None
            status["writable"] = None
            status["error"] = f"os_error: {exc}"
        out["repos"][name] = status
    return out

