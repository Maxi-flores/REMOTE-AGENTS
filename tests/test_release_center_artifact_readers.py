from __future__ import annotations

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

from release_center.artifact_readers import (  # noqa: E402
    read_gate_trace,
    read_latest_readiness_report,
    read_release_artifact_history,
)


class TestReleaseCenterArtifactReaders(unittest.TestCase):
    def test_readers_tolerate_missing_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.assertEqual(read_latest_readiness_report(base / "missing.json"), {})
            self.assertEqual(read_gate_trace(base / "missing.json"), {})
            self.assertEqual(read_release_artifact_history(base / "missing.jsonl"), [])

    def test_readers_tolerate_malformed_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            bad = base / "bad.json"
            bad.write_text("{oops", encoding="utf-8")
            self.assertEqual(read_latest_readiness_report(bad), {})
            badl = base / "bad.jsonl"
            badl.write_text("{oops\n{}\n", encoding="utf-8")
            history = read_release_artifact_history(badl)
            self.assertEqual(len(history), 1)


if __name__ == "__main__":
    unittest.main()

