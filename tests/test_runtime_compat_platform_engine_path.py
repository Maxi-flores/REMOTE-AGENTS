from __future__ import annotations

import importlib
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


class TestRuntimeCompatPlatformEnginePath(unittest.TestCase):
    def test_legacy_and_canonical_paths_exist(self) -> None:
        legacy = REPO_ROOT / "src" / "orchastrator" / "platform_engine.py"
        canonical = REPO_ROOT / "src" / "orchestrator" / "platform_engine.py"
        self.assertTrue(legacy.exists())
        self.assertTrue(canonical.exists())

    def test_canonical_alias_points_to_legacy(self) -> None:
        mod = importlib.import_module("orchestrator.platform_engine")
        legacy_path = Path(getattr(mod, "_LEGACY_PLATFORM_ENGINE"))
        expected = REPO_ROOT / "src" / "orchastrator" / "platform_engine.py"
        self.assertEqual(legacy_path.resolve(), expected.resolve())


if __name__ == "__main__":
    unittest.main()

