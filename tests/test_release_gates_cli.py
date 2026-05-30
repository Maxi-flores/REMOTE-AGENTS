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

from release_gates.cli import main  # noqa: E402


class TestReleaseGatesCli(unittest.TestCase):
    def _seed_base(self, base: Path) -> Path:
        cp = base / ".control_plane"
        su = base / ".sentient_ui"
        rr = base / ".release_reports"
        cfg = base / "config" / "release_gates"
        scenario_cfg = cfg / "scenario_packs"
        promotion_cfg = cfg / "promotion_profiles"
        cp.mkdir(parents=True, exist_ok=True)
        su.mkdir(parents=True, exist_ok=True)
        rr.mkdir(parents=True, exist_ok=True)
        cfg.mkdir(parents=True, exist_ok=True)
        scenario_cfg.mkdir(parents=True, exist_ok=True)
        promotion_cfg.mkdir(parents=True, exist_ok=True)

        (cfg / "default_gate_policy.json").write_text(
            json.dumps(
                {
                    "policy_id": "default_gate_policy",
                    "display_name": "Default",
                    "minimum_readiness_score": 80,
                    "block_on_critical_findings": True,
                    "block_on_malformed_artifacts": True,
                    "block_on_missing_artifacts": True,
                    "block_on_unsupported_versions": True,
                    "max_warning_count": 10,
                    "max_error_count": 2,
                    "required_artifacts": ["control_plane_snapshot", "sentient_ui_view_model"],
                    "advisory_only": True,
                    "metadata": {},
                }
            ),
            encoding="utf-8",
        )
        (cfg / "strict_gate_policy.json").write_text(
            json.dumps(
                {
                    "policy_id": "strict_gate_policy",
                    "display_name": "Strict",
                    "minimum_readiness_score": 95,
                    "block_on_critical_findings": True,
                    "block_on_malformed_artifacts": True,
                    "block_on_missing_artifacts": True,
                    "block_on_unsupported_versions": True,
                    "max_warning_count": 0,
                    "max_error_count": 0,
                    "required_artifacts": ["control_plane_snapshot", "sentient_ui_view_model"],
                    "advisory_only": True,
                    "metadata": {},
                }
            ),
            encoding="utf-8",
        )
        (cfg / "experimental_gate_policy.json").write_text(
            json.dumps(
                {
                    "policy_id": "experimental_gate_policy",
                    "display_name": "Experimental",
                    "minimum_readiness_score": 50,
                    "block_on_critical_findings": False,
                    "block_on_malformed_artifacts": False,
                    "block_on_missing_artifacts": False,
                    "block_on_unsupported_versions": False,
                    "max_warning_count": 100,
                    "max_error_count": 50,
                    "required_artifacts": [],
                    "advisory_only": True,
                    "metadata": {},
                }
            ),
            encoding="utf-8",
        )
        (scenario_cfg / "default_release_scenarios.json").write_text(
            json.dumps(
                {
                    "scenario_pack_id": "default_release_scenarios",
                    "display_name": "Default Scenarios",
                    "description": "Compare all baseline profiles.",
                    "policy_names": [
                        "default_gate_policy",
                        "strict_gate_policy",
                        "experimental_gate_policy",
                    ],
                    "comparison_strategy": "compare_all",
                    "advisory_only": True,
                    "metadata": {},
                }
            ),
            encoding="utf-8",
        )
        (promotion_cfg / "dev_promotion_profile.json").write_text(
            json.dumps(
                {
                    "profile_id": "dev_promotion_profile",
                    "display_name": "Dev",
                    "target_environment": "dev",
                    "required_scenario_pack": "default_release_scenarios",
                    "minimum_aggregate_status": "review_required",
                    "allowed_aggregate_decisions": ["pass", "pass_with_warnings", "mixed"],
                    "require_no_blockers": False,
                    "require_rollback_plan": False,
                    "require_ci_handoff": False,
                    "max_warning_count": 100,
                    "max_error_count": 10,
                    "advisory_only": True,
                    "metadata": {},
                }
            ),
            encoding="utf-8",
        )
        (promotion_cfg / "staging_promotion_profile.json").write_text(
            json.dumps(
                {
                    "profile_id": "staging_promotion_profile",
                    "display_name": "Staging",
                    "target_environment": "staging",
                    "required_scenario_pack": "default_release_scenarios",
                    "minimum_aggregate_status": "review_required",
                    "allowed_aggregate_decisions": ["pass", "pass_with_warnings", "mixed"],
                    "require_no_blockers": True,
                    "require_rollback_plan": True,
                    "require_ci_handoff": False,
                    "max_warning_count": 25,
                    "max_error_count": 0,
                    "advisory_only": True,
                    "metadata": {},
                }
            ),
            encoding="utf-8",
        )
        (promotion_cfg / "production_promotion_profile.json").write_text(
            json.dumps(
                {
                    "profile_id": "production_promotion_profile",
                    "display_name": "Production",
                    "target_environment": "production",
                    "required_scenario_pack": "default_release_scenarios",
                    "minimum_aggregate_status": "ready",
                    "allowed_aggregate_decisions": ["pass"],
                    "require_no_blockers": True,
                    "require_rollback_plan": True,
                    "require_ci_handoff": True,
                    "max_warning_count": 0,
                    "max_error_count": 0,
                    "advisory_only": True,
                    "metadata": {},
                }
            ),
            encoding="utf-8",
        )
        report = rr / "release_readiness.json"
        report.write_text(
            json.dumps(
                {
                    "report_id": "r1",
                    "readiness_score": 95,
                    "blockers": [],
                    "warnings": [],
                    "findings": [],
                    "checked_artifacts": [
                        {"artifact_type": "control_plane_snapshot"},
                        {"artifact_type": "sentient_ui_view_model"},
                    ],
                    "readiness_status": "ready",
                }
            ),
            encoding="utf-8",
        )
        return report

    def test_cli_list_print_export_modes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            report = self._seed_base(base)
            out = io.StringIO()
            code = main(["--list-policies", "--base-dir", tmp], stdout=out)
            self.assertEqual(code, 0)
            self.assertIn("default_gate_policy", out.getvalue())

            out = io.StringIO()
            code = main(["--policy", "default_gate_policy", "--print", "--base-dir", tmp], stdout=out)
            self.assertEqual(code, 0)
            payload = json.loads(out.getvalue())
            self.assertIn("decision", payload)

            out = io.StringIO()
            code = main(["--policy", "default_gate_policy", "--export", "--base-dir", tmp], stdout=out)
            self.assertEqual(code, 0)
            self.assertTrue((base / ".release_reports" / "gate_trace.json").exists())

            out = io.StringIO()
            code = main(["--policy", "default_gate_policy", "--export-jsonl", "--base-dir", tmp], stdout=out)
            self.assertEqual(code, 0)
            self.assertTrue((base / ".release_reports" / "gate_traces.jsonl").exists())

    def test_cli_scenario_list_compare_export_modes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _ = self._seed_base(base)
            out = io.StringIO()
            code = main(["--list-scenarios", "--base-dir", tmp], stdout=out)
            self.assertEqual(code, 0)
            self.assertIn("default_release_scenarios", out.getvalue())

            out = io.StringIO()
            code = main(
                [
                    "--scenario-pack",
                    "default_release_scenarios",
                    "--compare",
                    "--print",
                    "--base-dir",
                    tmp,
                ],
                stdout=out,
            )
            self.assertEqual(code, 0)
            payload = json.loads(out.getvalue())
            self.assertIn("comparison", payload)

            out = io.StringIO()
            code = main(
                [
                    "--scenario-pack",
                    "default_release_scenarios",
                    "--compare",
                    "--export",
                    "--base-dir",
                    tmp,
                ],
                stdout=out,
            )
            self.assertEqual(code, 0)
            self.assertTrue((base / ".release_reports" / "scenario_comparison.json").exists())

            out = io.StringIO()
            code = main(
                [
                    "--scenario-pack",
                    "default_release_scenarios",
                    "--compare",
                    "--export-jsonl",
                    "--base-dir",
                    tmp,
                ],
                stdout=out,
            )
            self.assertEqual(code, 0)
            self.assertTrue((base / ".release_reports" / "scenario_comparisons.jsonl").exists())

    def test_cli_promotion_list_plan_export_modes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            _ = self._seed_base(base)

            # Seed a scenario report consumed by promotion planner.
            scenario_report_path = base / ".release_reports" / "scenario_comparison.json"
            scenario_report_path.write_text(
                json.dumps(
                    {
                        "comparison": {
                            "comparison_id": "cmp_1",
                            "scenario_pack_id": "default_release_scenarios",
                            "aggregate_status": "ready",
                            "aggregate_decision": "pass",
                            "blockers": [],
                            "warnings": [],
                            "summary": {"decision_counts": {"blocked": 0}},
                            "policy_decisions": [],
                        }
                    }
                ),
                encoding="utf-8",
            )
            scenario_before = scenario_report_path.read_text(encoding="utf-8")

            out = io.StringIO()
            code = main(["--list-promotion-profiles", "--base-dir", tmp], stdout=out)
            self.assertEqual(code, 0)
            self.assertIn("dev_promotion_profile", out.getvalue())

            out = io.StringIO()
            code = main(
                [
                    "--profile",
                    "dev_promotion_profile",
                    "--plan-promotion",
                    "--print",
                    "--base-dir",
                    tmp,
                ],
                stdout=out,
            )
            self.assertEqual(code, 0)
            payload = json.loads(out.getvalue())
            self.assertIn("recommendations", payload)

            out = io.StringIO()
            code = main(
                [
                    "--profile",
                    "staging_promotion_profile",
                    "--plan-promotion",
                    "--export",
                    "--base-dir",
                    tmp,
                ],
                stdout=out,
            )
            self.assertEqual(code, 0)
            self.assertTrue((base / ".release_reports" / "promotion_recommendations.json").exists())

            out = io.StringIO()
            code = main(
                [
                    "--profile",
                    "production_promotion_profile",
                    "--plan-promotion",
                    "--export-jsonl",
                    "--base-dir",
                    tmp,
                ],
                stdout=out,
            )
            self.assertEqual(code, 0)
            self.assertTrue((base / ".release_reports" / "promotion_recommendations.jsonl").exists())
            scenario_after = scenario_report_path.read_text(encoding="utf-8")
            self.assertEqual(scenario_before, scenario_after)

    def test_source_report_not_modified(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            report = self._seed_base(base)
            before = report.read_text(encoding="utf-8")
            _ = main(["--policy", "default_gate_policy", "--print", "--base-dir", tmp], stdout=io.StringIO())
            after = report.read_text(encoding="utf-8")
            self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
