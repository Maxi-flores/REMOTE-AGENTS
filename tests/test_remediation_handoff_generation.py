from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from remediation_handoff.generator import generate_implementation_package_report  # noqa: E402


class TestRemediationHandoffGeneration(unittest.TestCase):
    def test_generates_packages(self) -> None:
        remediation_report = {
            "report_id": "rr1",
            "batches": [{"batch_id": "b1", "name": "Batch", "priority": "P1", "repository": "REMOTE-AGENTS", "item_ids": ["i1"]}],
            "items": [
                {
                    "item_id": "i1",
                    "title": "Add CLI without matching CLI test: mission_engine",
                    "category": "tests",
                    "suggested_action": "Add tests",
                }
            ],
        }
        report = generate_implementation_package_report(remediation_report=remediation_report)
        self.assertEqual(len(report["packages"]), 1)
        package = report["packages"][0]
        self.assertIn("codex_prompt", package)
        self.assertIn("prompt_text", package["codex_prompt"])

    def test_reads_default_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            d = root / ".control_plane" / "remediation_plans"
            d.mkdir(parents=True, exist_ok=True)
            (d / "latest.json").write_text(json.dumps({"report_id": "rr", "batches": [], "items": []}), encoding="utf-8")
            report = generate_implementation_package_report(base_dir=root)
            self.assertIn("report_id", report)


if __name__ == "__main__":
    unittest.main()
