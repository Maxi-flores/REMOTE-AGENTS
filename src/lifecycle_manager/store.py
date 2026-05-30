from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

from lifecycle_manager.capability_contracts import validate_capability_profile_dict
from lifecycle_manager.lifecycle_contracts import validate_lifecycle_state_dict


class LifecycleStore:
    def __init__(self, path: str | Path = ".lifecycle/agents.json") -> None:
        self.path = Path(path)

    def load_state(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {"schema_version": 1, "capability_profiles": {}, "lifecycle_states": {}, "events": []}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {"schema_version": 1, "capability_profiles": {}, "lifecycle_states": {}, "events": []}
        if not isinstance(payload, dict):
            return {"schema_version": 1, "capability_profiles": {}, "lifecycle_states": {}, "events": []}
        payload.setdefault("schema_version", 1)
        payload.setdefault("capability_profiles", {})
        payload.setdefault("lifecycle_states", {})
        payload.setdefault("events", [])
        return payload

    def save_state(self, state: Dict[str, Any]) -> None:
        self._ensure_lifecycle_path()
        tmp = self.path.with_name(f".{self.path.name}.tmp")
        with tmp.open("w", encoding="utf-8") as handle:
            json.dump(state, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(tmp, self.path)

    def upsert_capability_profile(self, profile: Dict[str, Any]) -> None:
        validate_capability_profile_dict(profile)
        state = self.load_state()
        profiles = state.get("capability_profiles")
        if not isinstance(profiles, dict):
            profiles = {}
            state["capability_profiles"] = profiles
        profiles[str(profile["agent_class"])] = profile
        self.save_state(state)

    def get_capability_profile(self, agent_class: str) -> Dict[str, Any] | None:
        state = self.load_state()
        profiles = state.get("capability_profiles")
        if not isinstance(profiles, dict):
            return None
        rec = profiles.get(agent_class)
        return rec if isinstance(rec, dict) else None

    def list_capability_profiles(self) -> List[Dict[str, Any]]:
        state = self.load_state()
        profiles = state.get("capability_profiles")
        if not isinstance(profiles, dict):
            return []
        return [v for v in profiles.values() if isinstance(v, dict)]

    def register_agent(self, lifecycle_state: Dict[str, Any]) -> None:
        validate_lifecycle_state_dict(lifecycle_state)
        state = self.load_state()
        agents = state.get("lifecycle_states")
        if not isinstance(agents, dict):
            agents = {}
            state["lifecycle_states"] = agents
        agents[str(lifecycle_state["agent_id"])] = lifecycle_state
        self.save_state(state)

    def get_agent(self, agent_id: str) -> Dict[str, Any] | None:
        state = self.load_state()
        agents = state.get("lifecycle_states")
        if not isinstance(agents, dict):
            return None
        rec = agents.get(agent_id)
        return rec if isinstance(rec, dict) else None

    def update_agent_health(self, agent_id: str, health: str) -> None:
        state = self.load_state()
        agents = state.get("lifecycle_states")
        if not isinstance(agents, dict):
            return
        rec = agents.get(agent_id)
        if not isinstance(rec, dict):
            return
        rec["health"] = health
        self.save_state(state)

    def update_agent_availability(self, agent_id: str, availability: str) -> None:
        state = self.load_state()
        agents = state.get("lifecycle_states")
        if not isinstance(agents, dict):
            return
        rec = agents.get(agent_id)
        if not isinstance(rec, dict):
            return
        rec["availability"] = availability
        self.save_state(state)

    def list_agents(self) -> List[Dict[str, Any]]:
        state = self.load_state()
        agents = state.get("lifecycle_states")
        if not isinstance(agents, dict):
            return []
        return [v for v in agents.values() if isinstance(v, dict)]

    def append_lifecycle_event(self, event: Dict[str, Any]) -> None:
        state = self.load_state()
        events = state.get("events")
        if not isinstance(events, list):
            events = []
            state["events"] = events
        events.append(event)
        self.save_state(state)

    def _ensure_lifecycle_path(self) -> None:
        normalized = str(self.path).replace("\\", "/")
        if "/.lifecycle/" not in f"/{normalized}":
            raise ValueError("lifecycle store path must be under .lifecycle/")
        self.path.parent.mkdir(parents=True, exist_ok=True)

