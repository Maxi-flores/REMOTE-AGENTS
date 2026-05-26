from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping


def dump_critical_misalignment(logs_dir: Path, state: dict, exc: Exception) -> Path:
    logs_dir.mkdir(parents=True, exist_ok=True)
    path = logs_dir / "CRITICAL_MISALIGNMENT.json"
    snapshot = {
        "pipeline_state": "DEAD_HALT",
        "error": repr(exc),
        "state": state,
    }
    path.write_text(json.dumps(snapshot, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def _diff_json(observed: Any, expected: Any, *, path: str = "$", limit: int = 200) -> list[dict[str, Any]]:
    """Structural JSON diff for dissent snapshots (bounded, deterministic)."""

    diffs: list[dict[str, Any]] = []

    def _push(kind: str, p: str, a: Any, b: Any) -> None:
        if len(diffs) >= limit:
            return
        diffs.append({"path": p, "kind": kind, "observed": a, "expected": b})

    def _walk(a: Any, b: Any, p: str) -> None:
        if len(diffs) >= limit:
            return
        if type(a) is not type(b):
            _push("type_mismatch", p, type(a).__name__, type(b).__name__)
            return
        if isinstance(a, dict):
            a_keys = set(a.keys())
            b_keys = set(b.keys())
            for k in sorted(a_keys - b_keys):
                _push("unexpected_key", f"{p}.{k}", a.get(k), None)
            for k in sorted(b_keys - a_keys):
                _push("missing_key", f"{p}.{k}", None, b.get(k))
            for k in sorted(a_keys & b_keys):
                _walk(a.get(k), b.get(k), f"{p}.{k}")
            return
        if isinstance(a, list):
            if len(a) != len(b):
                _push("length_mismatch", p, len(a), len(b))
            for idx, (ai, bi) in enumerate(zip(a, b)):
                _walk(ai, bi, f"{p}[{idx}]")
            return
        if a != b:
            _push("value_mismatch", p, a, b)

    _walk(observed, expected, path)
    return diffs


def dump_quorum_dissent_snapshot(
    logs_dir: Path,
    *,
    stage: str,
    correlation_id: str,
    handshake_hash: str,
    envelope_signature: str,
    proposer_payload: Mapping[str, Any],
    ballots: Mapping[str, Mapping[str, Any]],
) -> Path:
    """Write a detailed quorum conflict layout to logs/QUORUM_DISSENT_SNAPSHOT.json."""

    logs_dir.mkdir(parents=True, exist_ok=True)
    path = logs_dir / "QUORUM_DISSENT_SNAPSHOT.json"

    dissenting: dict[str, Any] = {}
    for vid, ballot in ballots.items():
        if not bool(ballot.get("passed")):
            dissenting[vid] = dict(ballot)

    validator_diffs: dict[str, Any] = {}
    for vid, ballot in dissenting.items():
        observed = ballot.get("observed")
        expected = ballot.get("expected")
        if observed is not None and expected is not None:
            validator_diffs[vid] = _diff_json(observed, expected)

    snapshot = {
        "event": "QUORUM_DISSENT",
        "stage": stage,
        "correlation_id": correlation_id,
        "handshake_hash": handshake_hash,
        "envelope_signature": envelope_signature,
        "proposer_payload": proposer_payload,
        "ballots": dict((k, dict(v)) for k, v in ballots.items()),
        "dissenting_ballots": dissenting,
        "structural_diffs": validator_diffs,
    }
    path.write_text(json.dumps(snapshot, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
