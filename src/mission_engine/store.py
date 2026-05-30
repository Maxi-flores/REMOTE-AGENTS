from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path
from typing import Any

from .contracts import (
    ApprovalRecord,
    ConsensusRecord,
    Mission,
    MissionStatus,
    MissionTask,
    utc_now,
    validate_approval_record_dict,
    validate_consensus_record_dict,
    validate_mission_dict,
)


class MissionStore:
    """Durable JSON storage for Mission Engine MVP state."""

    def __init__(self, root_dir: str | Path = ".missions") -> None:
        self.root_dir = Path(root_dir)
        self.archive_dir = self.root_dir / "archived"

    def create_mission(self, mission: Mission) -> Mission:
        self.root_dir.mkdir(parents=True, exist_ok=True)
        path = self._mission_path(mission.mission_id)
        if path.exists():
            raise FileExistsError(f"mission already exists: {mission.mission_id}")
        mission.updated_utc = utc_now()
        self._atomic_write(path, mission.to_dict())
        return mission

    def read_mission(self, mission_id: str) -> Mission:
        path = self._mission_path(mission_id)
        data = self._read_json(path)
        return Mission.from_dict(data)

    def write_mission(self, mission: Mission) -> Mission:
        mission.updated_utc = utc_now()
        self._atomic_write(self._mission_path(mission.mission_id), mission.to_dict())
        return mission

    def update_mission_status(
        self,
        mission_id: str,
        status: MissionStatus,
        *,
        failure_reason: str | None = None,
    ) -> Mission:
        mission = self.read_mission(mission_id)
        mission.status = status
        if failure_reason is not None:
            mission.failure_reason = str(failure_reason)
        return self.write_mission(mission)

    def append_telemetry_event(self, mission_id: str, event: dict[str, Any]) -> Mission:
        mission = self.read_mission(mission_id)
        payload = dict(event)
        payload.setdefault("ts_utc", utc_now())
        mission.telemetry_events.append(payload)
        return self.write_mission(mission)

    def append_task(self, mission_id: str, task: MissionTask) -> Mission:
        mission = self.read_mission(mission_id)
        if task.mission_id != mission.mission_id:
            raise ValueError("task mission_id does not match mission")
        mission.tasks.append(task)
        if mission.status == "draft":
            mission.status = "planned"
        return self.write_mission(mission)

    def append_approval(self, mission_id: str, approval_record: ApprovalRecord | dict[str, Any]) -> Mission:
        mission = self.read_mission(mission_id)
        record = approval_record.to_dict() if isinstance(approval_record, ApprovalRecord) else dict(approval_record)
        validate_approval_record_dict(record)
        if record["mission_id"] != mission.mission_id:
            raise ValueError("approval mission_id does not match mission")
        mission.approvals.append(record)
        return self.write_mission(mission)

    def append_consensus_record(
        self,
        mission_id: str,
        consensus_record: ConsensusRecord | dict[str, Any],
    ) -> Mission:
        mission = self.read_mission(mission_id)
        record = consensus_record.to_dict() if isinstance(consensus_record, ConsensusRecord) else dict(consensus_record)
        validate_consensus_record_dict(record)
        if record["mission_id"] != mission.mission_id:
            raise ValueError("consensus mission_id does not match mission")
        mission.consensus_records.append(record)
        return self.write_mission(mission)

    def archive_mission(self, mission_id: str) -> Path:
        mission = self.update_mission_status(mission_id, "archived")
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        src = self._mission_path(mission.mission_id)
        dst = self.archive_dir / src.name
        if dst.exists():
            stamp = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
            dst = self.archive_dir / f"{src.stem}.{stamp}{src.suffix}"
        shutil.move(os.fspath(src), os.fspath(dst))
        return dst

    def _mission_path(self, mission_id: str) -> Path:
        safe = "".join(ch if (ch.isalnum() or ch in ("-", "_")) else "_" for ch in str(mission_id))[:120]
        if not safe:
            raise ValueError("mission_id is required")
        return self.root_dir / f"{safe}.json"

    def _read_json(self, path: Path) -> dict[str, Any]:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError(f"mission file must contain object: {path}")
        validate_mission_dict(data)
        return data

    def _atomic_write(self, path: Path, payload: dict[str, Any]) -> None:
        validate_mission_dict(payload)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f".{path.name}.tmp.{os.getpid()}.{int(time.time() * 1000)}")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
