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

from handoff_refinement.refiner import generate_refinement_report  # noqa: E402


class TestHandoffRefinementRefiner(unittest.TestCase):
    def test_splits_broad_package(self) -> None:
        handoff = {
            "report_id": "h1",
            "packages": [
                {
                    "package_id": "p1",
                    "source_batch_id": "b1",
                    "title": "broad",
                    "objective": "obj",
                    "target_files": [
                        "tests/test_mission_engine_cli.py",
                        "tests/test_mission_engine.py",
                        "tests/test_orchastrator.py",
                        "tests/test_orchestrator.py",
                        "tests/test_routers.py",
                        "tests/test_tools.py",
                        "tests/test_ui.py",
                    ],
                    "expected_changes": {"file_additions": [], "file_updates": [], "notes": []},
                    "validation_commands": [
                        "python -m unittest tests.test_mission_engine_cli -v",
                        "python -m unittest tests.test_mission_engine -v",
                        "python -m unittest tests.test_orchastrator -v",
                        "python -m unittest tests.test_orchestrator -v",
                    ],
                    "codex_prompt": {"prompt_id": "old_prompt"},
                }
            ],
        }
        report = generate_refinement_report(handoff_report=handoff)
        refined = report["refined_packages"]
        self.assertGreaterEqual(len(refined), 4)
        for pkg in refined:
            self.assertIn("source_package_id", pkg)
            self.assertIn("source_batch_id", pkg)
            self.assertIn("codex_prompt", pkg)


if __name__ == "__main__":
    unittest.main()
