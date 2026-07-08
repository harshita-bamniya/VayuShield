from fastapi import Request
from fastapi.responses import JSONResponse


class VayuShieldError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400, details: dict | None = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class NotFoundError(VayuShieldError):
    def __init__(self, message: str = "Resource not found"):
        super().__init__("NOT_FOUND", message, 404)


class UnauthorizedError(VayuShieldError):
    def __init__(self, message: str = "Authentication required"):
        super().__init__("UNAUTHORIZED", message, 401)


class ForbiddenError(VayuShieldError):
    def __init__(self, message: str = "Access denied"):
        super().__init__("FORBIDDEN", message, 403)


class ConflictError(VayuShieldError):
    def __init__(self, message: str, details: dict | None = None):
        super().__init__("CONFLICT", message, 409, details)


class ValidationError(VayuShieldError):
    def __init__(self, message: str, details: dict | None = None):
        super().__init__("VALIDATION_ERROR", message, 422, details)


async def vayushield_exception_handler(request: Request, exc: VayuShieldError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "data": None,
            "meta": None,
            "error": {"code": exc.code, "message": exc.message, "details": exc.details},
        },
    )
