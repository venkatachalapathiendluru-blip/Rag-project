"""FastAPI application: uvicorn backend.main:app"""

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import psycopg
from psycopg_pool import PoolTimeout
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend import config, ingestion
from backend.db import close_pool, connection, migrate, pending_migrations
from backend.errors import ApiError
from backend.routers import chat, documents, evaluations, system
from backend.telemetry import configure_logging, request_context


logger = logging.getLogger("rag.app")


@asynccontextmanager
async def lifespan(_app):
    configure_logging()

    try:
        with connection() as conn:
            # Schema changes are a deployment step: python -m backend.migrate
            applied = migrate(conn) if config.AUTO_MIGRATE else []
            pending = pending_migrations(conn)

            if pending:
                # /ready/ reports this too. Nothing is changed.
                logger.warning(f"migrations_pending={pending} run: python -m backend.migrate")

            recovered = ingestion.recover_interrupted_jobs(conn) if not pending else 0

        if applied or recovered:
            logger.info(f"startup applied={applied} recovered_jobs={recovered}")
    except (psycopg.Error, PoolTimeout) as error:
        # The API still starts, and /ready/ reports what is wrong.
        logger.error("database_unavailable_at_startup", extra={"error_type": type(error).__name__})

    yield
    close_pool()


def _error(request, status_code, code, message, details=None):
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "details": details,
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )


def create_app():
    app = FastAPI(
        title="Enterprise RAG Platform",
        version="1.0.0",
        lifespan=lifespan,
        docs_url=f"{config.API_PREFIX}/docs",
        openapi_url=f"{config.API_PREFIX}/openapi.json",
    )

    if config.CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.CORS_ORIGINS,
            allow_methods=["GET", "POST", "PUT", "DELETE"],
            allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
        )

    app.middleware("http")(request_context)

    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, error: ApiError):
        return _error(request, error.status_code, error.code, error.message, error.details)

    @app.exception_handler(RequestValidationError)
    async def handle_validation(request: Request, error: RequestValidationError):
        details = [
            {"field": ".".join(str(part) for part in item["loc"]), "problem": item["msg"]}
            for item in error.errors()
        ]
        return _error(request, 422, "invalid_request", "The request is not valid.", details)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http(request: Request, error: StarletteHTTPException):
        return _error(request, error.status_code, "http_error", str(error.detail))

    @app.exception_handler(psycopg.Error)
    async def handle_database(request: Request, error: psycopg.Error):
        logger.error("database_error", extra={"error_type": type(error).__name__})
        return _error(request, 503, "database_unavailable", "The database is unavailable.")

    @app.exception_handler(PoolTimeout)
    async def handle_pool(request: Request, _error_value: PoolTimeout):
        return _error(request, 503, "database_unavailable", "The database is unavailable.")

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, error: Exception):
        logger.exception("unhandled_error", extra={"error_type": type(error).__name__})
        return _error(request, 500, "internal_error", "Something went wrong on the server.")

    for router in (system.public, system.router, chat.router, documents.router, evaluations.router):
        app.include_router(router, prefix=config.API_PREFIX)

    return app


app = create_app()
