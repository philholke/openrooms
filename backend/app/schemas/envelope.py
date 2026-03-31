from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ErrorDetail(BaseModel):
    field: str | None = None
    message: str
    code: str | None = None


class Meta(BaseModel):
    page: int
    per_page: int
    total: int


class Envelope(BaseModel, Generic[T]):
    data: T
    meta: Meta | None = None
    errors: list[ErrorDetail] | None = None


class PaginatedEnvelope(BaseModel, Generic[T]):
    data: list[T]
    meta: Meta
    errors: list[ErrorDetail] | None = None


# ---------------------------------------------------------------------------
# Helper constructors
# ---------------------------------------------------------------------------

def ok(data: T) -> dict:
    """Wrap a single item or pre-built payload in the standard envelope."""
    return {"data": data, "meta": None, "errors": None}


def paginated(data: list, *, page: int, per_page: int, total: int) -> dict:
    """Wrap a list with pagination metadata."""
    return {
        "data": data,
        "meta": {"page": page, "per_page": per_page, "total": total},
        "errors": None,
    }


def error(errors: list[ErrorDetail], status_code: int = 400) -> dict:
    """Build an error envelope (caller still needs to set the HTTP status)."""
    return {
        "data": None,
        "meta": None,
        "errors": [e.model_dump() for e in errors],
    }
