"""FastAPI application factory: routers, uniform error bodies, CORS and lifespan."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Awaitable, Callable, MutableMapping
from contextlib import asynccontextmanager
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import scheduler
from app.config import get_settings
from app.db import init_db
from app.routers import deals, health, refresh, sources, stores
from app.schemas import ErrorBody, ErrorInfo

logger = logging.getLogger(__name__)

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]

_STATUS_CODES: dict[int, str] = {
    400: "bad_request",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    422: "validation_error",
    429: "rate_limited",
    500: "internal_error",
    501: "not_implemented",
    503: "service_unavailable",
}


def error_response(
    status_code: int,
    code: str,
    message: str,
    details: list[dict[str, Any]] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    """Build a response carrying the uniform ErrorBody."""
    body = ErrorBody(error=ErrorInfo(code=code, message=message, details=details))
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(body),
        headers=headers,
    )


def _default_message(status_code: int) -> str:
    try:
        return HTTPStatus(status_code).phrase
    except ValueError:
        return "Error"


async def _http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    status_code = exc.status_code
    code = _STATUS_CODES.get(status_code, "http_error")
    message = _default_message(status_code)
    details: list[dict[str, Any]] | None = None
    detail = exc.detail
    if isinstance(detail, dict):
        code = str(detail.get("code") or code)
        message = str(detail.get("message") or message)
        raw_details = detail.get("details")
        if isinstance(raw_details, list):
            details = jsonable_encoder(raw_details)
    elif isinstance(detail, str) and detail and detail != message:
        message = detail
    return error_response(status_code, code, message, details, headers=exc.headers)


async def _validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    details = [
        {
            "loc": list(error.get("loc", ())),
            "msg": str(error.get("msg", "")),
            "type": str(error.get("type", "")),
        }
        for error in exc.errors()
    ]
    return error_response(422, "validation_error", "Invalid request parameters", details)


async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled error on %s %s", request.method, request.url.path)
    return error_response(500, "internal_error", "Internal Server Error")


class UnhandledErrorMiddleware:
    """Turns an unhandled exception into a 500 ErrorBody INSIDE the CORS layer.

    Starlette sends responses for unhandled exceptions from its outermost
    middleware, outside CORS, so the browser would see a CORS failure instead
    of the error. This middleware sits beneath CORSMiddleware and answers
    first. No stack trace ever reaches the client.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        started = False

        async def send_wrapper(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            logger.exception("unhandled error on %s %s", scope.get("method"), scope.get("path"))
            if started:
                raise
            response = error_response(500, "internal_error", "Internal Server Error")
            await response(scope, receive, send)


def _configure_logging() -> None:
    # Privacy (AC-20): never log visitor IP addresses or User-Agents. The
    # access log is the only place either would appear, so it stays off even
    # when uvicorn is started without --no-access-log.
    logging.getLogger("uvicorn.access").disabled = True
    # Logs carry scraper runs and source errors only, not every outgoing request.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
        )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    _configure_logging()
    # Read and validate the whole configuration once, so a bad value refuses
    # to start with a message naming the variable.
    settings = get_settings()
    logger.info(
        "starting: database=%s refresh_interval_hours=%g scrape_on_start=%s",
        settings.database_path,
        settings.refresh_interval_hours,
        settings.scrape_on_start,
    )
    init_db()
    scheduler.start_scheduler()
    try:
        yield
    finally:
        scheduler.stop_scheduler()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Gratis-Spiele-Scraper API",
        version="1.0.0",
        lifespan=lifespan,
        redirect_slashes=False,
    )

    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_exception_handler)
    app.add_exception_handler(Exception, _unhandled_exception_handler)

    # Order matters: the middleware added last is the outermost one, so CORS
    # wraps the error middleware and every error response keeps its headers.
    app.add_middleware(UnhandledErrorMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    for module in (health, deals, stores, sources, refresh):
        app.include_router(module.router)
    return app


app = create_app()
