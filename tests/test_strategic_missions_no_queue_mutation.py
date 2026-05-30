from __future__ import annotations

import io
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

from strategic_missions.cli import main  # noqa: E402


class TestStrategicMissionsNoQueueMutation(unittest.TestCase):
    def test_queue_file_not_modified(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / ".control_plane" / "executive").mkdir(parents=True, exist_ok=True)
            (base / ".control_plane" / "executive" / "executive_briefing.json").write_text(
                json.dumps(
                    {
                        "overall_status": "degraded",
                        "top_risks": [
                            {
                                "finding_id": "f1",
                                "severity": "high",
                                "category": "lifecycle",
                                "title": "No capability profiles present",
                                "description": "desc",
                                "recommended_action": "Create lifecycle profiles",
                            }
                        ],
                        "recommended_actions": ["Create lifecycle profiles"],
                    }
                ),
                encoding="utf-8",
            )
            queue_path = base / ".platform_queue" / "next_task.json"
            queue_path.parent.mkdir(parents=True, exist_ok=True)
            queue_path.write_text('{"instruction":"existing"}\n', encoding="utf-8")
            before = queue_path.read_text(encoding="utf-8")
            code = main(["--export", "--base-dir", tmp], stdout=io.StringIO())
            self.assertEqual(code, 0)
            after = queue_path.read_text(encoding="utf-8")
            self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()

