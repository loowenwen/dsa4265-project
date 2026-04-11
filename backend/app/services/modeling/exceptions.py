"""Service-level exception types."""

from __future__ import annotations


class ModelUnavailableError(RuntimeError):
    """Raised when a required model cannot be loaded or executed."""

    def __init__(self, message: str, model_path: str, cause: str | None = None) -> None:
        super().__init__(message)
        self.model_path = model_path
        self.cause = cause

