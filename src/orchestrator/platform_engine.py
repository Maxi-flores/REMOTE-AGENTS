"""Canonical platform engine entrypoint.

The original implementation lives in ``src/orchastrator/platform_engine.py``.
That misspelled path remains supported for existing launch commands while new
callers can use ``src/orchestrator/platform_engine.py``.
"""

from __future__ import annotations

import importlib.util
import runpy
from pathlib import Path
from types import ModuleType
from typing import Any


_LEGACY_PLATFORM_ENGINE = Path(__file__).resolve().parents[1] / "orchastrator" / "platform_engine.py"


def _load_legacy_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("_remote_agents_legacy_platform_engine", _LEGACY_PLATFORM_ENGINE)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load legacy platform engine at {_LEGACY_PLATFORM_ENGINE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_legacy: ModuleType | None = None


def _legacy_module() -> ModuleType:
    global _legacy
    if _legacy is None:
        _legacy = _load_legacy_module()
    return _legacy


def __getattr__(name: str) -> Any:
    return getattr(_legacy_module(), name)


def main() -> None:
    runpy.run_path(str(_LEGACY_PLATFORM_ENGINE), run_name="__main__")


if __name__ == "__main__":
    main()
