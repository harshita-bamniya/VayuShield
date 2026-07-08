from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginationMeta(BaseModel):
    page: int
    limit: int
    total: int


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, str] = {}


class ApiEnvelope(BaseModel, Generic[T]):
    data: T | None = None
    meta: PaginationMeta | None = None
    error: ErrorDetail | None = None

    @classmethod
    def ok(cls, data: T, meta: PaginationMeta | None = None) -> "ApiEnvelope[T]":
        return cls(data=data, meta=meta, error=None)

    @classmethod
    def err(cls, code: str, message: str, details: dict | None = None) -> "ApiEnvelope[None]":
        return cls(data=None, meta=None, error=ErrorDetail(code=code, message=message, details=details or {}))
