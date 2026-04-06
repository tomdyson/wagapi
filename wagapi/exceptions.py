from __future__ import annotations


class WagapiError(Exception):
    """Base exception for wagapi."""

    exit_code: int = 1


class UsageError(WagapiError):
    """Invalid CLI usage."""

    exit_code = 2


class NetworkError(WagapiError):
    """Connection or network error."""

    exit_code = 3


class AuthError(WagapiError):
    """Authentication failed (401)."""

    exit_code = 4


class PermissionDeniedError(WagapiError):
    """Permission denied (403)."""

    exit_code = 5


class NotFoundError(WagapiError):
    """Resource not found (404)."""

    exit_code = 6


class ValidationError(WagapiError):
    """Validation error (400/422)."""

    exit_code = 7

    def __init__(self, message: str, details: dict | list | None = None):
        super().__init__(message)
        self.details = details
