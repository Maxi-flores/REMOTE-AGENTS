from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence, TextIO

from release_gates.policy_loader import list_available_gate_policies, load_named_gate_policy
from release_gates.promotion_loader import (
    list_available_promotion_profiles,
    load_named_promotion_profile,
)
from release_gates.promotion_planner import plan_promotion
from release_gates.promotion_reports import (
    append_promotion_report_jsonl,
    build_promotion_report,
    write_promotion_report,
)
from release_gates.scenario_loader import list_available_scenario_packs, load_named_scenario_pack
from release_gates.multi_simulator import simulate_scenario_pack
from release_gates.scenario_reports import (
    append_scenario_report_jsonl,
    build_scenario_report,
    write_scenario_report,
)
from release_gates.simulator import simulate_gate
from release_gates.traces import append_gate_trace_jsonl, build_gate_trace, write_gate_trace


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Advisory release gate simulator CLI.")
    parser.add_argument("--policy", default="default_gate_policy")
    parser.add_argument("--print", action="store_true", dest="print_decision")
    parser.add_argument("--export", action="store_true")
    parser.add_argument("--export-jsonl", action="store_true")
    parser.add_argument("--list-policies", action="store_true")
    parser.add_argument("--list-scenarios", action="store_true")
    parser.add_argument("--scenario-pack")
    parser.add_argument("--compare", action="store_true")
    parser.add_argument("--list-promotion-profiles", action="store_true")
    parser.add_argument("--profile", default="dev_promotion_profile")
    parser.add_argument("--plan-promotion", action="store_true")
    parser.add_argument("--plan-all-promotions", action="store_true")
    parser.add_argument("--base-dir", default=".")
    return parser


def main(argv: Sequence[str] | None = None, *, stdout: TextIO | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    out = stdout or sys.stdout
    base = Path(args.base_dir)

    if args.list_policies:
        payload = {"policies": list_available_gate_policies(base / "config" / "release_gates")}
        out.write(json.dumps(payload, indent=2, sort_keys=True))
        out.write("\n")
        return 0
    if args.list_scenarios:
        payload = {
            "scenario_packs": list_available_scenario_packs(base / "config" / "release_gates" / "scenario_packs")
        }
        out.write(json.dumps(payload, indent=2, sort_keys=True))
        out.write("\n")
        return 0
    if args.list_promotion_profiles:
        payload = {
            "promotion_profiles": list_available_promotion_profiles(
                base / "config" / "release_gates" / "promotion_profiles"
            )
        }
        out.write(json.dumps(payload, indent=2, sort_keys=True))
        out.write("\n")
        return 0

    report_path = base / ".release_reports" / "release_readiness.json"
    if report_path.exists():
        report = json.loads(report_path.read_text(encoding="utf-8"))
    else:
        report = {
            "report_id": None,
            "readiness_score": 0,
            "blockers": ["release readiness report missing"],
            "warnings": [],
            "findings": [],
            "checked_artifacts": [],
            "readiness_status": "unknown",
        }

    if args.plan_promotion or args.plan_all_promotions:
        scenario_report_path = base / ".release_reports" / "scenario_comparison.json"
        if scenario_report_path.exists():
            scenario_report = json.loads(scenario_report_path.read_text(encoding="utf-8"))
        else:
            scenario_report = {"comparison": {"aggregate_status": "unknown", "aggregate_decision": "unknown"}}
        comparison = scenario_report.get("comparison", scenario_report) if isinstance(scenario_report, dict) else {}
        comparison = comparison if isinstance(comparison, dict) else {}
        if args.plan_all_promotions:
            profile_names = list_available_promotion_profiles(base / "config" / "release_gates" / "promotion_profiles")
        else:
            profile_names = [args.profile]
        recommendations = []
        for profile_name in profile_names:
            profile = load_named_promotion_profile(
                profile_name, base_dir=base / "config" / "release_gates" / "promotion_profiles"
            )
            recommendations.append(plan_promotion(comparison, profile))
        promotion_report = build_promotion_report(recommendations, scenario_report if isinstance(scenario_report, dict) else {})
        if args.export:
            path = write_promotion_report(
                promotion_report,
                path=base / ".release_reports" / "promotion_recommendations.json",
            )
            result = {"recommendations": recommendations, "promotion_report_path": str(path)}
        elif args.export_jsonl:
            path = append_promotion_report_jsonl(
                promotion_report,
                path=base / ".release_reports" / "promotion_recommendations.jsonl",
            )
            result = {"recommendations": recommendations, "promotion_report_path": str(path)}
        else:
            result = {"recommendations": recommendations, "scenario_report_found": scenario_report_path.exists()}
    elif args.compare:
        scenario_name = args.scenario_pack or "default_release_scenarios"
        scenario_pack = load_named_scenario_pack(scenario_name, base_dir=base / "config" / "release_gates" / "scenario_packs")
        comparison = simulate_scenario_pack(report if isinstance(report, dict) else {}, scenario_pack)
        scenario_report = build_scenario_report(comparison, report if isinstance(report, dict) else {}, scenario_pack)
        if args.export:
            path = write_scenario_report(scenario_report, path=base / ".release_reports" / "scenario_comparison.json")
            result = {"comparison": comparison, "scenario_report_path": str(path)}
        elif args.export_jsonl:
            path = append_scenario_report_jsonl(
                scenario_report, path=base / ".release_reports" / "scenario_comparisons.jsonl"
            )
            result = {"comparison": comparison, "scenario_report_path": str(path)}
        else:
            result = {"comparison": comparison, "scenario_pack": scenario_pack}
    else:
        policy = load_named_gate_policy(args.policy, base_dir=base / "config" / "release_gates")
        decision = simulate_gate(report if isinstance(report, dict) else {}, policy)
        trace = build_gate_trace(decision, report if isinstance(report, dict) else {}, policy)
        if args.export:
            path = write_gate_trace(trace, path=base / ".release_reports" / "gate_trace.json")
            result = {"decision": decision, "trace_path": str(path)}
        elif args.export_jsonl:
            path = append_gate_trace_jsonl(trace, path=base / ".release_reports" / "gate_traces.jsonl")
            result = {"decision": decision, "trace_path": str(path)}
        else:
            result = {"decision": decision, "policy": policy}

    if args.print_decision or not (args.export or args.export_jsonl):
        out.write(json.dumps(result, indent=2, sort_keys=True))
        out.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
