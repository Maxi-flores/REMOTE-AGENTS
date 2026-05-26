"""Runtime exceptions for the autonomous office."""

from __future__ import annotations


class CriticalMisalignmentError(RuntimeError):
    """Raised when a twin validation audit fails and the pipeline must halt."""

    code = "CRITICAL_MISALIGNMENT"


class SchemaMismatchedException(Exception):
    """Raised when a packet fails schema validation."""


class PipelineHaltException(Exception):
    """Raised when handshake auditing detects an unrecoverable pipeline fault."""
