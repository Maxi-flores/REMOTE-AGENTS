from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .contracts import MissionTask, utc_now


@dataclass(frozen=True, slots=True)
class QueueAdapterResult:
    enqueued: bool
    blocked: bool
    queue_path: str
    payload: dict[str, Any] | None = None
    reason: str | None = None


class MissionQueueAdapter:
    """Adapter from MissionTask to the legacy single-flight queue file."""

    def __init__(self, queue_file: str | Path = ".platform_queue/next_task.json") -> None:
        self.queue_file = Path(queue_file)

    def build_payload(self, task: MissionTask) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "task_id": task.task_id,
            "mission_id": task.mission_id,
            "instruction": task.instruction,
            "priority": int(task.priority),
            "target_repository": task.target_repository,
            "source": "mission-engine",
            "enqueued_utc": utc_now(),
        }
        return payload

    def enqueue_task(self, task: MissionTask) -> QueueAdapterResult:
        payload = self.build_payload(task)
        self.queue_file.parent.mkdir(parents=True, exist_ok=True)
        data = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

        fd: int | None = None
        try:
            fd = os.open(os.fspath(self.queue_file), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
        except FileExistsError:
            return QueueAdapterResult(
                enqueued=False,
                blocked=True,
                queue_path=os.fspath(self.queue_file),
                payload=payload,
                reason="legacy queue slot already occupied",
            )

        try:
            with os.fdopen(fd, "wb") as f:
                fd = None
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
        finally:
            if fd is not None:
                os.close(fd)

        return QueueAdapterResult(
            enqueued=True,
            blocked=False,
            queue_path=os.fspath(self.queue_file),
            payload=payload,
        )

