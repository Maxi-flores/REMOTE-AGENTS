from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from scheduler.contracts import (
    LEASE_STATUSES,
    WORKER_STATUSES,
    TaskLease,
    WorkerDescriptor,
    utc_now,
    validate_task_lease_dict,
    validate_worker_descriptor_dict,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATE_PATH = REPO_ROOT / ".scheduler" / "state.json"


class SchedulerStateStore:
    def __init__(self, state_path: Optional[Path] = None) -> None:
        self.state_path = Path(state_path) if state_path is not None else DEFAULT_STATE_PATH

    def load_state(self) -> Dict[str, Any]:
        if not self.state_path.exists():
            return _empty_state()
        with self.state_path.open("r", encoding="utf-8") as f:
            state = json.load(f)
        if not isinstance(state, dict):
            return _empty_state()
        state.setdefault("schema_version", 1)
        state.setdefault("workers", {})
        state.setdefault("leases", {})
        state.setdefault("scheduler_events", [])
        for worker in state.get("workers", {}).values():
            if isinstance(worker, dict):
                validate_worker_descriptor_dict(worker)
        for lease in state.get("leases", {}).values():
            if isinstance(lease, dict):
                validate_task_lease_dict(lease)
        if not isinstance(state.get("scheduler_events"), list):
            state["scheduler_events"] = []
        return state

    def save_state(self, state: Dict[str, Any]) -> None:
        normalized = {
            "schema_version": int(state.get("schema_version", 1)),
            "workers": dict(state.get("workers") or {}),
            "leases": dict(state.get("leases") or {}),
            "scheduler_events": list(state.get("scheduler_events") or []),
        }
        for worker in normalized["workers"].values():
            if isinstance(worker, dict):
                validate_worker_descriptor_dict(worker)
        for lease in normalized["leases"].values():
            if isinstance(lease, dict):
                validate_task_lease_dict(lease)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.state_path.with_name(f".{self.state_path.name}.tmp")
        with tmp_path.open("w", encoding="utf-8") as f:
            json.dump(normalized, f, indent=2, sort_keys=True)
            f.write("\n")
        os.replace(tmp_path, self.state_path)

    def register_worker(self, worker: WorkerDescriptor | Dict[str, Any]) -> Dict[str, Any]:
        payload = worker.to_dict() if isinstance(worker, WorkerDescriptor) else dict(worker)
        validate_worker_descriptor_dict(payload)
        state = self.load_state()
        existing = state["workers"].get(payload["worker_id"], {})
        if isinstance(existing, dict):
            payload["metadata"] = {**existing.get("metadata", {}), **payload.get("metadata", {})}
        state["workers"][payload["worker_id"]] = payload
        self.save_state(state)
        return payload

    def update_worker_status(self, worker_id: str, status: str) -> Dict[str, Any]:
        if status not in WORKER_STATUSES:
            raise ValueError(f"Invalid worker status: {status}")
        state = self.load_state()
        worker = state["workers"].get(worker_id)
        if not isinstance(worker, dict):
            raise KeyError(f"worker not found: {worker_id}")
        worker["status"] = status
        worker["updated_utc"] = utc_now()
        validate_worker_descriptor_dict(worker)
        self.save_state(state)
        return worker

    def create_lease(self, lease: TaskLease | Dict[str, Any]) -> Dict[str, Any]:
        payload = lease.to_dict() if isinstance(lease, TaskLease) else dict(lease)
        validate_task_lease_dict(payload)
        state = self.load_state()
        existing = state["leases"].get(payload["lease_id"], {})
        if isinstance(existing, dict):
            payload["metadata"] = {**existing.get("metadata", {}), **payload.get("metadata", {})}
        state["leases"][payload["lease_id"]] = payload
        self.save_state(state)
        return payload

    def renew_lease(self, lease_id: str, expires_utc: str) -> Dict[str, Any]:
        state = self.load_state()
        lease = state["leases"].get(lease_id)
        if not isinstance(lease, dict):
            raise KeyError(f"lease not found: {lease_id}")
        lease["lease_status"] = "renewed"
        lease["expires_utc"] = expires_utc
        lease["renewed_utc"] = utc_now()
        validate_task_lease_dict(lease)
        self.save_state(state)
        return lease

    def release_lease(self, lease_id: str) -> Dict[str, Any]:
        state = self.load_state()
        lease = state["leases"].get(lease_id)
        if not isinstance(lease, dict):
            raise KeyError(f"lease not found: {lease_id}")
        lease["lease_status"] = "released"
        lease["released_utc"] = utc_now()
        validate_task_lease_dict(lease)
        self.save_state(state)
        return lease

    def expire_stale_leases(self, now_utc: str) -> List[Dict[str, Any]]:
        state = self.load_state()
        expired: List[Dict[str, Any]] = []
        for lease in state["leases"].values():
            if not isinstance(lease, dict):
                continue
            if lease.get("lease_status") not in {"active", "renewed"}:
                continue
            expires_utc = str(lease.get("expires_utc") or "")
            if expires_utc and expires_utc <= now_utc:
                lease["lease_status"] = "expired"
                lease["released_utc"] = now_utc
                validate_task_lease_dict(lease)
                expired.append(dict(lease))
        if expired:
            self.save_state(state)
        return expired

    def list_workers(self) -> List[Dict[str, Any]]:
        workers = self.load_state()["workers"]
        return [dict(worker) for worker in workers.values() if isinstance(worker, dict)]

    def list_active_leases(self) -> List[Dict[str, Any]]:
        leases = self.load_state()["leases"]
        return [
            dict(lease)
            for lease in leases.values()
            if isinstance(lease, dict) and lease.get("lease_status") in {"active", "renewed"}
        ]

    def append_scheduler_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        payload = dict(event)
        payload.setdefault("created_utc", utc_now())
        state = self.load_state()
        state["scheduler_events"].append(payload)
        self.save_state(state)
        return payload


def _empty_state() -> Dict[str, Any]:
    return {"schema_version": 1, "workers": {}, "leases": {}, "scheduler_events": []}
