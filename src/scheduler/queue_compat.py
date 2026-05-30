from __future__ import annotations

from pathlib import Path
from typing import Any, Dict


def describe_legacy_queue_contract() -> Dict[str, Any]:
    return {
        "queue_path": ".platform_queue/next_task.json",
        "lock_path": ".platform_queue/processing.lock",
        "failed_path": ".platform_queue/failed/",
        "queue_type": "single_file_single_flight",
        "scheduler_mutates_queue": False,
        "compatibility_note": "Phase 6 scheduler metadata does not replace or write the legacy queue.",
    }


def can_enqueue_with_single_file_queue(queue_path: str | Path = ".platform_queue/next_task.json") -> bool:
    return not Path(queue_path).exists()


def explain_queue_backpressure(
    queue_path: str | Path = ".platform_queue/next_task.json",
    lock_path: str | Path = ".platform_queue/processing.lock",
) -> Dict[str, Any]:
    queue = Path(queue_path)
    lock = Path(lock_path)
    queue_occupied = queue.exists()
    lock_present = lock.exists()
    if queue_occupied and lock_present:
        state = "queue_occupied_and_worker_processing"
    elif queue_occupied:
        state = "queue_slot_occupied"
    elif lock_present:
        state = "processing_lock_present"
    else:
        state = "queue_available"
    return {
        "queue_path": str(queue),
        "lock_path": str(lock),
        "queue_occupied": queue_occupied,
        "lock_present": lock_present,
        "can_enqueue": not queue_occupied,
        "state": state,
        "queue_mutation": False,
    }
