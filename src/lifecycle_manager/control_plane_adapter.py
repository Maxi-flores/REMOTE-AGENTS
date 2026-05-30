from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Dict

from lifecycle_manager.health import (
    detect_capability_gaps,
    detect_single_points_of_failure,
    summarize_lifecycle_health,
)
from lifecycle_manager.store import LifecycleStore
from lifecycle_manager.capability_registry import load_repositories_registry


def collect_lifecycle_summary(base_dir: str | Path = ".") -> Dict[str, Any]:
    root = Path(base_dir)
    store = LifecycleStore(root / ".lifecycle" / "agents.json")
    state = store.load_state()
    profiles = [v for v in state.get("capability_profiles", {}).values() if isinstance(v, dict)] if isinstance(state.get("capability_profiles"), dict) else []
    agents = [v for v in state.get("lifecycle_states", {}).values() if isinstance(v, dict)] if isinstance(state.get("lifecycle_states"), dict) else []
    health_summary = summarize_lifecycle_health(agents, profiles)
    repos_registry = load_repositories_registry(root / "config" / "registries" / "repositories.json")
    gaps = detect_capability_gaps(repos_registry, profiles)
    spof = detect_single_points_of_failure(profiles)
    coverage_counts = Counter()
    for profile in profiles:
        for repo in profile.get("repositories", []) if isinstance(profile.get("repositories"), list) else []:
            coverage_counts[str(repo)] += 1
    return {
        "capability_profile_count": len(profiles),
        "lifecycle_state_count": len(agents),
        "health_counts": health_summary.get("health_counts", {}),
        "availability_counts": health_summary.get("availability_counts", {}),
        "repository_coverage_counts": dict(coverage_counts),
        "capability_gap_count": len(gaps),
        "single_point_of_failure_count": len(spof),
    }

