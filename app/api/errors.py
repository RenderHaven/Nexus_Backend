"""
One error shape for the whole API.

Whatever fails — a raised HTTPException, a request that fails validation, or
an unhandled crash — the client receives the same object, so it never has to
branch on which endpoint it called.
"""
import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

# Default machine-readable code per status, used when the raiser didn't pick one.
STATUS_CODES: dict[int, str] = {
    400: "bad_request",
    401: "unauthenticated",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    422: "validation_error",
    429: "too_many_requests",
}


def error_body(
    code: str,
    message: str,
    payload: object | None = None,
) -> dict:
    return {
        "status": "error",
        "code": code,
        "message": message,
        "payload": payload,
    }


def _code_for(status_code: int) -> str:
    return STATUS_CODES.get(status_code, "error")


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        detail = exc.detail

        # A raiser can pass {"code": ..., "message": ...} for a specific code,
        # or a plain string for the default one.
        if isinstance(detail, dict):
            code = detail.get("code", _code_for(exc.status_code))
            message = detail.get("message", "")
            payload = detail.get("payload")
        else:
            code = _code_for(exc.status_code)
            message = str(detail)
            payload = None

        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(code, message, payload),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        fields = [
            {
                "field": ".".join(str(part) for part in err.get("loc", [])[1:]),
                "message": err.get("msg", ""),
            }
            for err in exc.errors()
        ]

        return JSONResponse(
            status_code=422,
            content=error_body(
                "validation_error",
                "The request could not be processed as sent",
                {"fields": fields},
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_body(
                "internal_error",
                "Something went wrong on our side",
            ),
        )
