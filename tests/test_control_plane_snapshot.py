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

from control_plane.snapshot import (  # noqa: E402
    build_control_plane_snapshot,
    export_control_plane_snapshot,
    export_control_plane_snapshot_jsonl,
)


class TestControlPlaneSnapshot(unittest.TestCase):
    def test_snapshot_builder_includes_major_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            snapshot = build_control_plane_snapshot(base_dir=Path(tmp))
            for key in (
                "runtime",
                "missions",
                "agents",
                "repositories",
                "tools",
                "scheduler",
                "memory_graph",
                "approvals",
                "consensus",
                "queue",
                "observability",
            ):
                self.assertIn(key, snapshot)
                self.assertIsInstance(snapshot[key], dict)

    def test_export_writes_only_under_control_plane(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            out = base / ".control_plane" / "snapshot.json"
            export_control_plane_snapshot(path=out, base_dir=base)
            self.assertTrue(out.exists())
            self.assertIn(".control_plane", str(out))
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertIsInstance(data, dict)

    def test_jsonl_export_appends_valid_json_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            out = base / ".control_plane" / "snapshots.jsonl"
            export_control_plane_snapshot_jsonl(path=out, base_dir=base)
            export_control_plane_snapshot_jsonl(path=out, base_dir=base)
            lines = [line for line in out.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(len(lines), 2)
            for line in lines:
                payload = json.loads(line)
                self.assertIsInstance(payload, dict)
                self.assertIn("snapshot_id", payload)


if __name__ == "__main__":
    unittest.main()

