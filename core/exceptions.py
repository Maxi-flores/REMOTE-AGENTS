"""Runtime exceptions for the autonomous office."""

from __future__ import annotations


class CriticalMisalignmentError(RuntimeError):
    """Raised when a twin validation audit fails and the pipeline must halt."""

    code = "CRITICAL_MISALIGNMENT"

