"""Application failures; HTTP representation belongs to exception handlers."""

from typing import Any


class AppException(Exception):
    code = "INTERNAL_ERROR"
    default_message = "Internal error"

    def __init__(self, message: str | None = None, details: dict[str, Any] | None = None):
        self.message = message if message is not None else self.default_message
        self.details = details or {}
        super().__init__(self.message)


class NotFoundException(AppException):
    code = "NOT_FOUND"
    default_message = "Resource not found"


class BadRequestException(AppException):
    code = "BAD_REQUEST"
    default_message = "Invalid request"


class UnauthorizedException(AppException):
    code = "UNAUTHORIZED"
    default_message = "Unauthorized"


class ForbiddenException(AppException):
    code = "FORBIDDEN"
    default_message = "Forbidden"


class InactiveAccountException(UnauthorizedException):
    code = "ACCOUNT_INACTIVE"
    default_message = "Employee account is not active"


class ConflictException(AppException):
    code = "CONFLICT"
    default_message = "Resource conflict"


class IncorrectIssueType(Exception):
    """The issue document belongs to the other issuing flow."""


class WorkflowNotImplemented(Exception):
    """Keep the existing unimplemented workflow behavior explicit."""
