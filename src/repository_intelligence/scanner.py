from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Set

from repository_intelligence.contracts import RepositoryInventory, new_id, utc_now, validate_repository_inventory_dict


IGNORED_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".control_plane",
    ".release_reports",
    ".sentient_ui",
    ".lifecycle",
    ".memory",
    ".scheduler",
    ".missions",
}

STATIC_RUNTIME_ENTRYPOINTS = [
    "run_autonomous_office.py",
    "src/orchastrator/platform_engine.py",
    "src/orchestrator/platform_engine.py",
    "src/orchestrator/gateway.py",
    "src/orchestrator/dispatcher.py",
]


def build_repository_inventory(base_dir: str | Path = ".") -> Dict[str, object]:
    root = Path(base_dir).resolve()
    source_dirs = _discover_source_directories(root)
    test_files = _discover_files(root, lambda p: p.parts and p.parts[0] == "tests" and p.name.startswith("test_") and p.suffix == ".py")
    docs_files = _discover_files(root, lambda p: p.parts and p.parts[0] == "docs" and p.suffix.lower() == ".md")
    config_files = _discover_files(root, lambda p: p.parts and p.parts[0] == "config" and p.suffix.lower() == ".json")
    package_files = _discover_package_files(root)
    runtime_entrypoints = _discover_runtime_entrypoints(root)

    inventory = RepositoryInventory(
        inventory_id=new_id("repo_inventory"),
        generated_utc=utc_now(),
        root_path=str(root),
        source_directories=source_dirs,
        test_files=test_files,
        documentation_files=docs_files,
        config_files=config_files,
        package_files=package_files,
        runtime_entrypoints=runtime_entrypoints,
        advisory_only=True,
        metadata={"advisory_only": True},
    ).to_dict()
    validate_repository_inventory_dict(inventory)
    return inventory


def _discover_source_directories(root: Path) -> List[str]:
    src = root / "src"
    if not src.exists() or not src.is_dir():
        return []
    dirs: List[str] = []
    for child in sorted(src.iterdir(), key=lambda p: p.name):
        if child.is_dir() and child.name not in IGNORED_DIRS and not child.name.startswith("."):
            dirs.append(_rel(root, child))
    return dirs


def _discover_files(root: Path, predicate) -> List[str]:
    out: List[str] = []
    for path in _walk_files(root):
        rel = path.relative_to(root)
        if predicate(rel):
            out.append(rel.as_posix())
    return sorted(out)


def _discover_package_files(root: Path) -> List[str]:
    candidates = ["README.md", "package.json", "requirements.txt"]
    files: List[str] = []
    for name in candidates:
        p = root / name
        if p.exists() and p.is_file():
            files.append(name)
    return files


def _discover_runtime_entrypoints(root: Path) -> List[str]:
    found: Set[str] = set()
    for rel in STATIC_RUNTIME_ENTRYPOINTS:
        if (root / rel).exists():
            found.add(rel.replace("\\", "/"))
    for path in _walk_files(root):
        rel = path.relative_to(root).as_posix()
        if rel.startswith("src/") and rel.endswith("/cli.py"):
            found.add(rel)
    return sorted(found)


def _walk_files(root: Path) -> Iterable[Path]:
    for current_root, dirnames, filenames in __import__("os").walk(root):
        current = Path(current_root)
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
        for filename in filenames:
            path = current / filename
            if any(part in IGNORED_DIRS for part in path.relative_to(root).parts):
                continue
            yield path


def _rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()

