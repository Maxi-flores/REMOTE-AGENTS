from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from repository_governance.contracts import (
    RepositoryAuditRecord,
    RepositoryGovernanceProfile,
    RepositoryHealthSnapshot,
    validate_audit_record_dict,
    validate_governance_profile_dict,
    validate_health_snapshot_dict,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GOVERNANCE_PATH = REPO_ROOT / ".governance" / "repositories.json"


class RepositoryGovernanceStore:
    def __init__(self, state_path: Optional[Path] = None) -> None:
        self.state_path = Path(state_path) if state_path is not None else DEFAULT_GOVERNANCE_PATH

    def load_state(self) -> Dict[str, Any]:
        if not self.state_path.exists():
            return _empty_state()
        with self.state_path.open("r", encoding="utf-8") as f:
            state = json.load(f)
        if not isinstance(state, dict):
            return _empty_state()
        state.setdefault("schema_version", 1)
        state.setdefault("profiles", {})
        state.setdefault("health_snapshots", {})
        state.setdefault("audit_records", {})
        for profile in state.get("profiles", {}).values():
            if isinstance(profile, dict):
                validate_governance_profile_dict(profile)
        for snapshots in state.get("health_snapshots", {}).values():
            if isinstance(snapshots, list):
                for snapshot in snapshots:
                    if isinstance(snapshot, dict):
                        validate_health_snapshot_dict(snapshot)
        for records in state.get("audit_records", {}).values():
            if isinstance(records, list):
                for record in records:
                    if isinstance(record, dict):
                        validate_audit_record_dict(record)
        return state

    def save_state(self, state: Dict[str, Any]) -> None:
        normalized = {
            "schema_version": int(state.get("schema_version", 1)),
            "profiles": dict(state.get("profiles") or {}),
            "health_snapshots": dict(state.get("health_snapshots") or {}),
            "audit_records": dict(state.get("audit_records") or {}),
        }
        for profile in normalized["profiles"].values():
            if isinstance(profile, dict):
                validate_governance_profile_dict(profile)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.state_path.with_name(f".{self.state_path.name}.tmp")
        with tmp_path.open("w", encoding="utf-8") as f:
            json.dump(normalized, f, indent=2, sort_keys=True)
            f.write("\n")
        os.replace(tmp_path, self.state_path)

    def upsert_profile(self, profile: RepositoryGovernanceProfile | Dict[str, Any]) -> Dict[str, Any]:
        payload = profile.to_dict() if isinstance(profile, RepositoryGovernanceProfile) else dict(profile)
        validate_governance_profile_dict(payload)
        state = self.load_state()
        existing = state["profiles"].get(payload["repository_name"], {})
        if isinstance(existing, dict):
            payload["metadata"] = {**existing.get("metadata", {}), **payload.get("metadata", {})}
        state["profiles"][payload["repository_name"]] = payload
        self.save_state(state)
        return payload

    def get_profile(self, repository_name: str) -> Optional[Dict[str, Any]]:
        profile = self.load_state()["profiles"].get(repository_name)
        return dict(profile) if isinstance(profile, dict) else None

    def list_profiles(self) -> List[Dict[str, Any]]:
        profiles = self.load_state()["profiles"]
        return [dict(profile) for profile in profiles.values() if isinstance(profile, dict)]

    def append_health_snapshot(self, snapshot: RepositoryHealthSnapshot | Dict[str, Any]) -> Dict[str, Any]:
        payload = snapshot.to_dict() if isinstance(snapshot, RepositoryHealthSnapshot) else dict(snapshot)
        validate_health_snapshot_dict(payload)
        state = self.load_state()
        state["health_snapshots"].setdefault(payload["repository_name"], []).append(payload)
        self.save_state(state)
        return payload

    def list_health_snapshots(self, repository_name: str) -> List[Dict[str, Any]]:
        snapshots = self.load_state()["health_snapshots"].get(repository_name, [])
        return [dict(snapshot) for snapshot in snapshots if isinstance(snapshot, dict)]

    def append_audit_record(self, record: RepositoryAuditRecord | Dict[str, Any]) -> Dict[str, Any]:
        payload = record.to_dict() if isinstance(record, RepositoryAuditRecord) else dict(record)
        validate_audit_record_dict(payload)
        state = self.load_state()
        state["audit_records"].setdefault(payload["repository_name"], []).append(payload)
        self.save_state(state)
        return payload

    def list_audit_records(self, repository_name: str) -> List[Dict[str, Any]]:
        records = self.load_state()["audit_records"].get(repository_name, [])
        return [dict(record) for record in records if isinstance(record, dict)]


def _empty_state() -> Dict[str, Any]:
    return {"schema_version": 1, "profiles": {}, "health_snapshots": {}, "audit_records": {}}
