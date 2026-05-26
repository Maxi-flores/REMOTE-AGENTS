"""Consensus-driven validation quorum engine (stdlib-only, Python 3.10+).

This module upgrades stage validation from single-auditor signoff into a small,
deterministic, BFT-inspired quorum registry. A stage may only commit its
workspace transaction when a configured threshold of validator ballots agrees.
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Any, Awaitable, Callable, Iterable, Mapping, MutableMapping, Sequence, TypedDict

from core.exceptions import QuorumDissentException
from core.fault import dump_quorum_dissent_snapshot
from core.hashutil import fnv1a_32
from core.schema import Schema, SchemaValidationError, canonical_json, validate_against_schema
from core.types import JSONObject, JSONValue


class BallotErrorClass(IntEnum):
    """Stable error classification indices for rejection ballots."""

    SCHEMA_VIOLATION = 1
    SECURITY_RISK = 2
    REGRESSION_INVENTORY = 3
    STRUCTURAL_DEVIATION = 4
    INTERNAL_ERROR = 5


class EnvelopeBallot(TypedDict, total=False):
    validator_id: str
    stage: str
    schema_id: str
    handshake_hash: str
    envelope_signature: str
    passed: bool
    error_class: int | None
    details: str
    observed: JSONValue
    expected: JSONValue
    ballot_signature: str


Validator = Callable[["ValidationContext"], Awaitable[EnvelopeBallot]]


@dataclass(frozen=True, slots=True)
class QuorumPolicy:
    mode: str = "unanimous"  # "unanimous" | "supermajority"
    halt_on_any_dissent: bool = True

    def required_passes(self, total: int) -> int:
        if total <= 0:
            return 0
        if self.mode == "unanimous":
            return total
        if self.mode == "supermajority":
            # > 2/3 of total.
            return (2 * total) // 3 + 1
        raise ValueError(f"Unknown quorum mode: {self.mode!r}")


@dataclass(frozen=True, slots=True)
class ValidationContext:
    stage: str
    schema: Schema
    payload: JSONObject
    envelope_signature: str
    handshake_hash: str
    source_role: str
    next_role: str
    correlation_id: str
    repo_root: Path


def _ballot_signature(ballot: EnvelopeBallot) -> str:
    material = dict(ballot)
    material.pop("ballot_signature", None)
    # Ensure deterministic serialization.
    canon = canonical_json(material)  # type: ignore[arg-type]
    return fnv1a_32(canon)


def _make_ballot(
    *,
    validator_id: str,
    ctx: ValidationContext,
    passed: bool,
    error_class: BallotErrorClass | None = None,
    details: str,
    observed: JSONValue | None = None,
    expected: JSONValue | None = None,
) -> EnvelopeBallot:
    ballot: EnvelopeBallot = {
        "validator_id": validator_id,
        "stage": ctx.stage,
        "schema_id": ctx.schema.schema_id,
        "handshake_hash": ctx.handshake_hash,
        "envelope_signature": ctx.envelope_signature,
        "passed": bool(passed),
        "error_class": int(error_class) if error_class is not None else None,
        "details": details,
    }
    if observed is not None:
        ballot["observed"] = observed
    if expected is not None:
        ballot["expected"] = expected
    ballot["ballot_signature"] = _ballot_signature(ballot)
    return ballot


def _iter_string_values(value: JSONValue) -> Iterable[str]:
    if isinstance(value, str):
        yield value
        return
    if value is None or isinstance(value, (int, float, bool)):
        return
    if isinstance(value, list):
        for item in value:
            yield from _iter_string_values(item)
        return
    if isinstance(value, dict):
        for v in value.values():
            yield from _iter_string_values(v)
        return


async def _schema_auditor(ctx: ValidationContext, *, validator_id: str) -> EnvelopeBallot:
    try:
        validate_against_schema(ctx.payload, ctx.schema.definition)
    except SchemaValidationError as exc:
        return _make_ballot(
            validator_id=validator_id,
            ctx=ctx,
            passed=False,
            error_class=BallotErrorClass.SCHEMA_VIOLATION,
            details=str(exc),
            observed={"schema_id": ctx.schema.schema_id},
            expected={"schema_id": ctx.schema.schema_id, "valid": True},
        )
    return _make_ballot(
        validator_id=validator_id,
        ctx=ctx,
        passed=True,
        details="schema_ok",
    )


_VULN_PATTERNS: Sequence[tuple[str, re.Pattern[str]]] = (
    ("eval", re.compile(r"\beval\s*\(", re.IGNORECASE)),
    ("exec", re.compile(r"\bexec\s*\(", re.IGNORECASE)),
    ("subprocess_shell", re.compile(r"\bshell\s*=\s*True\b", re.IGNORECASE)),
    ("sql_injection", re.compile(r"\b(drop\s+table|union\s+select)\b", re.IGNORECASE)),
    ("vulnerability_marker", re.compile(r"\bVULNERABILITY\b", re.IGNORECASE)),
)


async def _security_worker(ctx: ValidationContext, *, validator_id: str) -> EnvelopeBallot:
    hits: list[dict[str, str]] = []
    for text in _iter_string_values(ctx.payload):
        for name, pattern in _VULN_PATTERNS:
            if pattern.search(text):
                hits.append({"pattern": name, "snippet": text[:120]})
    if hits:
        return _make_ballot(
            validator_id=validator_id,
            ctx=ctx,
            passed=False,
            error_class=BallotErrorClass.SECURITY_RISK,
            details="security_patterns_detected",
            observed={"hits": hits},
            expected={"hits": []},
        )
    return _make_ballot(
        validator_id=validator_id,
        ctx=ctx,
        passed=True,
        details="security_ok",
    )


def _inventory_path(repo_root: Path) -> Path:
    # Repository-local, deterministic source of truth.
    return repo_root / "PF_REPO_INVENTORY_LIST"


async def _regression_worker(ctx: ValidationContext, *, validator_id: str) -> EnvelopeBallot:
    targets = ctx.payload.get("target_repositories")
    if not isinstance(targets, list) or not all(isinstance(x, str) for x in targets):
        return _make_ballot(
            validator_id=validator_id,
            ctx=ctx,
            passed=False,
            error_class=BallotErrorClass.STRUCTURAL_DEVIATION,
            details="target_repositories_invalid",
            observed={"target_repositories": targets},
            expected={"target_repositories": ["<repo-name>"]},
        )
    bad = [t for t in targets if not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", t)]
    if bad:
        return _make_ballot(
            validator_id=validator_id,
            ctx=ctx,
            passed=False,
            error_class=BallotErrorClass.REGRESSION_INVENTORY,
            details="invalid_repo_name",
            observed={"invalid": bad},
            expected={"pattern": r"^[A-Za-z0-9_.-]{1,64}$"},
        )

    inv = _inventory_path(ctx.repo_root)
    if not inv.exists():
        return _make_ballot(
            validator_id=validator_id,
            ctx=ctx,
            passed=True,
            details="inventory_missing_but_tolerated",
        )

    try:
        text = inv.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return _make_ballot(
            validator_id=validator_id,
            ctx=ctx,
            passed=False,
            error_class=BallotErrorClass.REGRESSION_INVENTORY,
            details=f"inventory_unreadable:{exc}",
            observed={"path": str(inv)},
            expected={"readable": True},
        )

    # Deterministic compatibility gate: inventory must be non-empty and well-formed enough to parse.
    has_table_header = "| Project |" in text and "| --- |" in text
    if not has_table_header:
        return _make_ballot(
            validator_id=validator_id,
            ctx=ctx,
            passed=False,
            error_class=BallotErrorClass.REGRESSION_INVENTORY,
            details="inventory_format_unrecognized",
            observed={"inventory_fingerprint": fnv1a_32(text[:4096])},
            expected={"contains": ["| Project |", "| --- |"]},
        )
    return _make_ballot(
        validator_id=validator_id,
        ctx=ctx,
        passed=True,
        details="regression_ok",
        observed={"inventory_fingerprint": fnv1a_32(text[:4096])},
    )


def _default_validators_for_stage(stage: str) -> Sequence[tuple[str, Validator]]:
    # Minimal, cross-functional validator set. IDs are stable telemetry keys.
    if stage == "architecture_to_risk":
        return (
            ("architecture_twin_auditor", lambda ctx: _schema_auditor(ctx, validator_id="architecture_twin_auditor")),
            ("security_validation_worker", lambda ctx: _security_worker(ctx, validator_id="security_validation_worker")),
            ("regression_consistency_worker", lambda ctx: _regression_worker(ctx, validator_id="regression_consistency_worker")),
        )
    if stage == "intake_to_architecture":
        return (
            ("intake_twin_auditor", lambda ctx: _schema_auditor(ctx, validator_id="intake_twin_auditor")),
            ("security_validation_worker", lambda ctx: _security_worker(ctx, validator_id="security_validation_worker")),
            ("regression_consistency_worker", lambda ctx: _regression_worker(ctx, validator_id="regression_consistency_worker")),
        )
    if stage == "risk_to_build_execution":
        return (
            ("risk_twin_auditor", lambda ctx: _schema_auditor(ctx, validator_id="risk_twin_auditor")),
            ("security_validation_worker", lambda ctx: _security_worker(ctx, validator_id="security_validation_worker")),
            ("regression_consistency_worker", lambda ctx: _regression_worker(ctx, validator_id="regression_consistency_worker")),
        )
    return (
        ("schema_auditor", lambda ctx: _schema_auditor(ctx, validator_id="schema_auditor")),
        ("security_validation_worker", lambda ctx: _security_worker(ctx, validator_id="security_validation_worker")),
        ("regression_consistency_worker", lambda ctx: _regression_worker(ctx, validator_id="regression_consistency_worker")),
    )


@dataclass(slots=True)
class ValidationQuorumManager:
    """Run parallel validators, aggregate ballots, and enforce quorum thresholds."""

    logs_dir: Path
    policy: QuorumPolicy = QuorumPolicy()
    validators_by_stage: Mapping[str, Sequence[tuple[str, Validator]]] | None = None

    async def validate(
        self,
        *,
        stage: str,
        schema: Schema,
        payload: JSONObject,
        envelope_signature: str,
        handshake_hash: str,
        source_role: str,
        next_role: str,
        correlation_id: str,
        repo_root: Path,
    ) -> dict[str, EnvelopeBallot]:
        ctx = ValidationContext(
            stage=stage,
            schema=schema,
            payload=payload,
            envelope_signature=envelope_signature,
            handshake_hash=handshake_hash,
            source_role=source_role,
            next_role=next_role,
            correlation_id=correlation_id,
            repo_root=repo_root,
        )

        validators = self._validators_for_stage(stage)
        ballots: MutableMapping[str, EnvelopeBallot] = {}

        async def _run_one(validator_id: str, validator: Validator) -> None:
            try:
                ballot = await validator(ctx)
            except Exception as exc:
                ballot = _make_ballot(
                    validator_id=validator_id,
                    ctx=ctx,
                    passed=False,
                    error_class=BallotErrorClass.INTERNAL_ERROR,
                    details=f"validator_exception:{exc!r}",
                )
            # Stabilize and enforce signatures even for custom validators.
            ballot["validator_id"] = validator_id
            ballot.setdefault("stage", ctx.stage)
            ballot.setdefault("schema_id", ctx.schema.schema_id)
            ballot.setdefault("handshake_hash", ctx.handshake_hash)
            ballot.setdefault("envelope_signature", ctx.envelope_signature)
            ballot.setdefault("passed", False)
            ballot.setdefault("error_class", None)
            ballot.setdefault("details", "")
            ballot["ballot_signature"] = _ballot_signature(ballot)
            ballots[validator_id] = ballot

        async with asyncio.TaskGroup() as tg:
            for validator_id, validator in validators:
                tg.create_task(_run_one(validator_id, validator))

        try:
            self._enforce_quorum(stage=stage, ballots=dict(ballots))
        except QuorumDissentException as exc:
            dump_quorum_dissent_snapshot(
                self.logs_dir,
                stage=stage,
                correlation_id=correlation_id,
                handshake_hash=handshake_hash,
                envelope_signature=envelope_signature,
                proposer_payload=payload,
                ballots=ballots,
            )
            raise QuorumDissentException(
                str(exc),
                stage=stage,
                correlation_id=correlation_id,
                handshake_hash=handshake_hash,
                envelope_signature=envelope_signature,
                ballots=dict(ballots),
                payload=payload,
            ) from exc
        return dict(ballots)

    def _validators_for_stage(self, stage: str) -> Sequence[tuple[str, Validator]]:
        if self.validators_by_stage is not None:
            validators = self.validators_by_stage.get(stage)
            if validators is not None:
                return validators
        return _default_validators_for_stage(stage)

    def _enforce_quorum(self, *, stage: str, ballots: Mapping[str, EnvelopeBallot]) -> None:
        total = len(ballots)
        required = self.policy.required_passes(total)
        passed = [b for b in ballots.values() if bool(b.get("passed"))]
        failed = [b for b in ballots.values() if not bool(b.get("passed"))]

        if len(passed) < required:
            raise QuorumDissentException(
                f"Quorum failed for {stage}: passed={len(passed)}/{total} required={required}"
            )
        if self.policy.halt_on_any_dissent and failed:
            dissenters = ",".join(sorted(str(b.get("validator_id")) for b in failed))
            raise QuorumDissentException(f"Quorum dissent for {stage}: dissenters={dissenters}")
