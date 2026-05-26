"""Runtime exceptions for the autonomous office."""

from __future__ import annotations


class CriticalMisalignmentError(RuntimeError):
    """Raised when a twin validation audit fails and the pipeline must halt."""

    code = "CRITICAL_MISALIGNMENT"


class SchemaMismatchedException(Exception):
    """Raised when a packet fails schema validation."""


class PipelineHaltException(Exception):
    """Raised when handshake auditing detects an unrecoverable pipeline fault."""


class QuorumDissentException(RuntimeError):
    """Raised when distributed validator ballots fail to reach quorum."""

    code = "QUORUM_DISSENT"

    def __init__(
        self,
        message: str,
        *,
        stage: str | None = None,
        correlation_id: str | None = None,
        handshake_hash: str | None = None,
        envelope_signature: str | None = None,
        ballots: object | None = None,
        payload: object | None = None,
    ) -> None:
        super().__init__(message)
        self.stage = stage
        self.correlation_id = correlation_id
        self.handshake_hash = handshake_hash
        self.envelope_signature = envelope_signature
        self.ballots = ballots
        self.payload = payload
