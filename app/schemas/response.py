from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """
    Envelope for endpoints that change something.

    Reads return their resource directly; writes wrap it so the client always
    has a message it can show and a predictable place to look for the result.
    """

    status: str = "success"
    message: str | None = None
    payload: T | None = None


class ErrorResponse(BaseModel):
    """Shape every failed request comes back in, whatever raised it."""

    status: str = "error"
    code: str
    message: str
    payload: Any | None = None


def success(
    message: str | None = None,
    payload: Any | None = None,
    **fields: Any,
) -> dict:
    """
    Build a success envelope.

        success("Post deleted", post_id=post_id)   -> payload {"post_id": ...}
        success("Post archived", payload=post)     -> payload is the post

    payload is always an object, never a bare value or list.
    """
    if payload is not None and fields:
        raise ValueError("Pass either a payload or named fields, not both")

    return {
        "status": "success",
        "message": message,
        "payload": payload if payload is not None else (fields or None),
    }
