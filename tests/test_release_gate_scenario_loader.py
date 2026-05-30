from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from release_gates.scenario_loader import (  # noqa: E402
    list_available_scenario_packs,
    load_named_scenario_pack,
    load_scenario_pack,
)


class TestReleaseGateScenarioLoader(unittest.TestCase):
    def test_scenario_pack_files_parse_and_validate(self) -> None:
        base = REPO_ROOT / "config" / "release_gates" / "scenario_packs"
        for name in (
            "default_release_scenarios.json",
            "production_release_scenarios.json",
            "experimental_release_scenarios.json",
        ):
            payload = load_scenario_pack(base / name)
            self.assertIn("scenario_pack_id", payload)

    def test_list_scenarios_returns_expected_packs(self) -> None:
        names = list_available_scenario_packs(REPO_ROOT / "config" / "release_gates" / "scenario_packs")
        self.assertIn("default_release_scenarios", names)
        self.assertIn("production_release_scenarios", names)
        self.assertIn("experimental_release_scenarios", names)

    def test_missing_scenario_returns_fallback(self) -> None:
        payload = load_named_scenario_pack("missing_scenario", base_dir=REPO_ROOT / "config" / "release_gates" / "scenario_packs" / "not_here")
        self.assertTrue(payload["metadata"]["fallback"])


if __name__ == "__main__":
    unittest.main()

