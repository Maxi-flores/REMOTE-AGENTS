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

from release_readiness.drift import (  # noqa: E402
    analyze_control_plane_jsonl,
    analyze_control_plane_snapshot,
    analyze_sentient_ui_view_model,
)


class TestReleaseReadinessDrift(unittest.TestCase):
    def test_analyzer_detects_missing_required_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "snapshot.json"
            path.write_text(json.dumps({"snapshot_id": "x", "schema_version": 1}), encoding="utf-8")
            findings = analyze_control_plane_snapshot(path)
            self.assertTrue(any(f["drift_type"] == "missing_required_field" for f in findings))

    def test_analyzer_detects_malformed_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "snapshot.json"
            path.write_text("{not_json", encoding="utf-8")
            findings = analyze_control_plane_snapshot(path)
            self.assertTrue(any(f["drift_type"] == "malformed_artifact" for f in findings))

    def test_analyzer_detects_missing_artifacts(self) -> None:
        findings = analyze_sentient_ui_view_model(Path("Z:/missing_view_model.json"))
        self.assertTrue(any(f["drift_type"] == "missing_artifact" for f in findings))

    def test_analyzer_handles_jsonl_invalid_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "snapshots.jsonl"
            path.write_text("{bad\n", encoding="utf-8")
            findings = analyze_control_plane_jsonl(path)
            self.assertTrue(any(f["drift_type"] == "jsonl_line_invalid" for f in findings))


if __name__ == "__main__":
    unittest.main()

