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

from handoff_refinement.grouping import (  # noqa: E402
    detect_broad_package,
    infer_change_type,
    infer_subsystem,
    split_groups,
)


class TestHandoffRefinementGrouping(unittest.TestCase):
    def test_inference(self) -> None:
        self.assertEqual(infer_subsystem("tests/test_mission_engine_cli.py"), "mission_engine")
        self.assertEqual(infer_change_type("tests/test_mission_engine_cli.py"), "add_cli_test")
        self.assertEqual(infer_change_type("tests/test_runtime_compat_queue_payload_shape.py"), "add_runtime_compat_test")

    def test_broad_detection_and_split(self) -> None:
        package = {
            "target_files": [
                "tests/test_mission_engine_cli.py",
                "tests/test_mission_engine.py",
                "tests/test_orchestrator.py",
                "tests/test_ui.py",
            ],
            "validation_commands": [
                "python -m unittest tests.test_mission_engine_cli -v",
                "python -m unittest tests.test_mission_engine -v",
                "python -m unittest tests.test_orchestrator -v",
            ],
        }
        broad, details = detect_broad_package(package)
        self.assertTrue(broad)
        self.assertIn("target_files_gt_3", details["reasons"])
        groups = split_groups(package)
        self.assertGreaterEqual(len(groups), 3)


if __name__ == "__main__":
    unittest.main()
