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

from sentient_ui.snapshot_reader import (  # noqa: E402
    read_latest_snapshot,
    read_snapshot_history,
    safe_snapshot_summary,
)


class TestSentientUiSnapshotReader(unittest.TestCase):
    def test_snapshot_reader_handles_missing_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            snapshot = read_latest_snapshot(Path(tmp) / ".control_plane" / "snapshot.json")
            self.assertEqual(snapshot, {})
            summary = safe_snapshot_summary(snapshot)
            self.assertTrue(summary["available"])

    def test_snapshot_reader_skips_malformed_jsonl_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".control_plane" / "snapshots.jsonl"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "\n".join(
                    [
                        json.dumps({"snapshot_id": "s1", "generated_utc": "t1"}),
                        "{not_json",
                        json.dumps({"snapshot_id": "s2", "generated_utc": "t2"}),
                    ]
                ),
                encoding="utf-8",
            )
            history = read_snapshot_history(path, limit=50)
            self.assertEqual(len(history), 2)
            self.assertEqual(history[0]["snapshot_id"], "s1")
            self.assertEqual(history[1]["snapshot_id"], "s2")


if __name__ == "__main__":
    unittest.main()

