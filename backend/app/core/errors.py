"""Domain errors raised by services and converted to HTTP responses in main.py.

Services stay independent of FastAPI; every error response has the shape {"detail": "..."}.
"""


class AppError(Exception):
    status_code = 400

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class BusinessRuleError(AppError):
    status_code = 400


class AuthenticationError(AppError):
    status_code = 401


class PermissionDeniedError(AppError):
    status_code = 403


class NotFoundError(AppError):
    status_code = 404


class ConflictError(AppError):
    status_code = 409
