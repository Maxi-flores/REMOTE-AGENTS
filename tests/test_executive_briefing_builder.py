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

from control_plane.bootstrap import bootstrap_advisory_artifacts  # noqa: E402
from executive_briefing.briefing_builder import build_executive_briefing, render_briefing_text  # noqa: E402
from executive_briefing.contracts import validate_executive_briefing_dict  # noqa: E402


class TestExecutiveBriefingBuilder(unittest.TestCase):
    def test_build_briefing_from_bootstrap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            bootstrap_advisory_artifacts(base)
            (base / ".control_plane" / "orchestration").mkdir(parents=True, exist_ok=True)
            (base / ".control_plane" / "orchestration" / "orchestration_report.json").write_text(
                json.dumps({"stage_results": [{"stage_name": "mission", "status": "ok"}]}),
                encoding="utf-8",
            )
            briefing = build_executive_briefing(base_dir=base)
            validate_executive_briefing_dict(briefing)
            text = render_briefing_text(briefing)
            self.assertIn("System Status:", text)


if __name__ == "__main__":
    unittest.main()

