"""Failures with contract-specific HTTP details."""


class DieuChinhError(Exception):
    def __init__(self, status: int, code: str, message: str, **extra):
        self.status, self.code, self.message, self.extra = status, code, message, extra
        super().__init__(message)
