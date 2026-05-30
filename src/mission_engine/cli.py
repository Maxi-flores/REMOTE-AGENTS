from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from mission_engine.contracts import create_mission, utc_now  # noqa: E402
from mission_engine.planner import plan_mission  # noqa: E402
from mission_engine.queue_adapter import MissionQueueAdapter  # noqa: E402
from mission_engine.store import MissionStore  # noqa: E402


def _split_repos(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Mission Engine MVP CLI.")
    parser.add_argument("--repo", help="Single target repository.")
    parser.add_argument("--repos", help="Comma-separated target repositories.")
    parser.add_argument("--title", required=True, help="Mission title.")
    parser.add_argument("--instruction", required=True, help="Mission instruction.")
    parser.add_argument("--priority", type=int, default=0, help="Mission priority.")
    parser.add_argument("--risk-tier", default="standard", help="Mission risk tier.")
    parser.add_argument("--enqueue", action="store_true", help="Enqueue the first pending task through the legacy queue.")
    parser.add_argument("--missions-dir", default=".missions", help="Mission storage directory.")
    parser.add_argument("--queue-file", default=".platform_queue/next_task.json", help="Legacy queue file path.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repos = _split_repos(args.repos)
    mission = create_mission(
        title=args.title,
        instruction=args.instruction,
        target_repository=args.repo,
        target_repositories=repos,
        priority=int(args.priority),
        risk_tier=args.risk_tier,
    )
    mission = plan_mission(mission)

    store = MissionStore(args.missions_dir)
    store.create_mission(mission)
    store.append_telemetry_event(
        mission.mission_id,
        {"event": "MISSION_CREATED", "task_count": len(mission.tasks), "ts_utc": utc_now()},
    )

    enqueue_result = None
    if args.enqueue:
        first_pending = next((task for task in mission.tasks if task.status == "pending"), None)
        if first_pending is not None:
            adapter = MissionQueueAdapter(args.queue_file)
            enqueue_result = adapter.enqueue_task(first_pending)
            mission = store.read_mission(mission.mission_id)
            for task in mission.tasks:
                if task.task_id == first_pending.task_id:
                    if enqueue_result.enqueued:
                        task.status = "queued"
                        task.queue_payload = enqueue_result.payload
                    elif enqueue_result.blocked:
                        task.status = "blocked"
                        task.queue_payload = enqueue_result.payload
                    task.updated_utc = utc_now()
            if enqueue_result.enqueued:
                mission.status = "scheduled"
            store.write_mission(mission)

    result = {
        "ok": True,
        "mission_id": mission.mission_id,
        "status": mission.status,
        "task_count": len(mission.tasks),
        "mission_path": str(Path(args.missions_dir) / f"{mission.mission_id}.json"),
    }
    if enqueue_result is not None:
        result["enqueue"] = {
            "enqueued": enqueue_result.enqueued,
            "blocked": enqueue_result.blocked,
            "reason": enqueue_result.reason,
            "queue_path": enqueue_result.queue_path,
        }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

