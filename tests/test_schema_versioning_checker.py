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

from schema_versioning.checker import (  # noqa: E402
    check_artifact_file,
    check_jsonl_artifact_file,
    check_sentient_ui_view_model_compatibility,
)


class TestSchemaVersioningChecker(unittest.TestCase):
    def test_checker_accepts_valid_control_plane_snapshot(self) -> None:
        result = check_artifact_file(REPO_ROOT / ".control_plane" / "snapshot.json", artifact_type="control_plane_snapshot")
        self.assertIn("is_compatible", result)

    def test_checker_rejects_malformed_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text("{not_json", encoding="utf-8")
            result = check_artifact_file(path, artifact_type="control_plane_snapshot")
            self.assertFalse(result["is_compatible"])

    def test_checker_accepts_valid_sentient_ui_view_model(self) -> None:
        vm = {
            "view_model_id": "vm_1",
            "generated_utc": "2026-01-01T00:00:00Z",
            "source_snapshot_id": "s1",
            "schema_version": 1,
            "runtime_panel": {},
            "mission_panel": {},
            "agent_panel": {},
            "repository_panel": {},
            "tool_panel": {},
            "scheduler_panel": {},
            "memory_panel": {},
            "approval_panel": {},
            "consensus_panel": {},
            "observability_panel": {},
            "alerts": [],
            "metadata": {},
        }
        result = check_sentient_ui_view_model_compatibility(vm)
        self.assertTrue(result["is_compatible"])

    def test_checker_rejects_malformed_view_model(self) -> None:
        result = check_sentient_ui_view_model_compatibility({"view_model_id": "x"})
        self.assertFalse(result["is_compatible"])

    def test_jsonl_checker_handles_valid_and_invalid_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "snapshots.jsonl"
            good = json.dumps(
                {
                    "snapshot_id": "s1",
                    "generated_utc": "t",
                    "schema_version": 1,
                    "runtime": {},
                    "missions": {},
                    "agents": {},
                    "repositories": {},
                    "tools": {},
                    "scheduler": {},
                    "memory_graph": {},
                    "approvals": {},
                    "consensus": {},
                    "queue": {},
                    "observability": {},
                    "metadata": {},
                }
            )
            path.write_text(good + "\n{bad\n", encoding="utf-8")
            result = check_jsonl_artifact_file(path, "control_plane_snapshot_jsonl")
            self.assertFalse(result["is_compatible"])
            self.assertEqual(result["metadata"]["invalid_lines"], 1)


if __name__ == "__main__":
    unittest.main()

