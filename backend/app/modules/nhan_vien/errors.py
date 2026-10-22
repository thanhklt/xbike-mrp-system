"""Employee policy failures carry their public contract code and HTTP status."""

from app.core.errors import AppException


class EmployeeError(AppException):
    def __init__(self, code: str, message: str, status_code: int):
        self.code = code
        self.status_code = status_code
        super().__init__(message)
