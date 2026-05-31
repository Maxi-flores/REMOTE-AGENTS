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

from portfolio_drift.analyzer import generate_portfolio_drift_report  # noqa: E402


class TestPortfolioDriftAnalyzer(unittest.TestCase):
    def test_generates_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".config" / "portfolio").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "portfolio_bootstrap").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "portfolio_onboarding_recommendations").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "portfolio_dependencies").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "portfolio_critical_path").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "portfolio_roadmap").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "portfolio_progress").mkdir(parents=True, exist_ok=True)
            (root / ".control_plane" / "portfolio").mkdir(parents=True, exist_ok=True)
            (root / ".config" / "portfolio" / "portfolio_registry.json").write_text(json.dumps({"repositories": [{"repository_id": "A", "enabled": True}]}), encoding="utf-8")
            (root / ".config" / "portfolio" / "dependencies.json").write_text(json.dumps({"dependencies": [{"repository_id": "A", "depends_on": []}]}), encoding="utf-8")
            (root / ".control_plane" / "portfolio_bootstrap" / "latest.json").write_text(json.dumps({"generated_utc": "2026-01-01T00:00:00Z", "onboarding_records": [{"repository_id": "A", "artifact_status": "none"}]}), encoding="utf-8")
            (root / ".control_plane" / "portfolio_onboarding_recommendations" / "latest.json").write_text(json.dumps({"generated_utc": "2026-01-01T00:00:00Z", "recommendations": []}), encoding="utf-8")
            (root / ".control_plane" / "portfolio_dependencies" / "latest.json").write_text(json.dumps({"generated_utc": "2026-01-01T00:00:00Z", "findings": []}), encoding="utf-8")
            (root / ".control_plane" / "portfolio_critical_path" / "latest.json").write_text(json.dumps({"generated_utc": "2026-01-01T00:00:00Z", "recommendations": []}), encoding="utf-8")
            (root / ".control_plane" / "portfolio_roadmap" / "latest.json").write_text(json.dumps({"generated_utc": "2026-01-01T00:00:00Z", "roadmap_items": []}), encoding="utf-8")
            (root / ".control_plane" / "portfolio_progress" / "latest.json").write_text(json.dumps({"generated_utc": "2026-01-01T00:00:00Z", "metrics": []}), encoding="utf-8")
            (root / ".control_plane" / "portfolio" / "latest.json").write_text(json.dumps({"generated_utc": "2026-01-01T00:00:00Z", "repository_statuses": []}), encoding="utf-8")
            report = generate_portfolio_drift_report(base_dir=root)
            self.assertIn("findings", report)
            self.assertIn("summary", report)


if __name__ == "__main__":
    unittest.main()

