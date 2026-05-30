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

from release_gates.traces import append_gate_trace_jsonl, build_gate_trace, write_gate_trace  # noqa: E402


class TestReleaseGatesTraces(unittest.TestCase):
    def test_trace_writer_writes_only_under_release_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            trace = build_gate_trace({"decision_id": "d1"}, {"report_id": "r1", "findings": []}, {"policy_id": "p1"})
            out = write_gate_trace(trace, path=base / ".release_reports" / "gate_trace.json")
            self.assertTrue(out.exists())
            self.assertIn(".release_reports", str(out))
            with self.assertRaises(ValueError):
                write_gate_trace(trace, path=base / "gate_trace.json")

    def test_jsonl_trace_appends_valid_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            trace = build_gate_trace({"decision_id": "d1"}, {"report_id": "r1", "findings": []}, {"policy_id": "p1"})
            out = base / ".release_reports" / "gate_traces.jsonl"
            append_gate_trace_jsonl(trace, path=out)
            append_gate_trace_jsonl(trace, path=out)
            lines = [line for line in out.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(len(lines), 2)
            for line in lines:
                payload = json.loads(line)
                self.assertIn("trace_id", payload)


if __name__ == "__main__":
    unittest.main()

