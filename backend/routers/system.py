"""Health, readiness, configuration, overview, metrics and settings."""

import os

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
import psycopg
from psycopg_pool import PoolTimeout

from backend import config, repositories, settings_repo
from backend.db import connection, pending_migrations
from backend.schemas import SettingsModel, SettingsUpdate
from backend.security import require_token
from backend.telemetry import metrics_summary
from tracing import TRACE_DIR


public = APIRouter(tags=["system"])
router = APIRouter(tags=["system"], dependencies=[Depends(require_token)])


def _models():
    return {
        "embedding_model": config.EMBEDDING_MODEL,
        "embedding_dimensions": config.EMBEDDING_DIMENSIONS,
        "generation_model": os.getenv("NVIDIA_MODEL") or None,
        "reranker_model": os.getenv("NVIDIA_RERANK_MODEL") or None,
    }


def _database_status():
    try:
        with connection() as conn:
            conn.execute("SELECT 1")
            pending = pending_migrations(conn)
    except (psycopg.Error, PoolTimeout, RuntimeError):
        return {"ok": False, "detail": "unreachable"}

    if pending:
        return {"ok": False, "detail": "migrations_pending", "pending": pending}

    return {"ok": True, "detail": "connected"}


@public.get("/health/")
def health():
    return {"status": "ok"}


@public.get("/ready/")
def ready():
    database = _database_status()
    provider_configured = bool(os.getenv("NVIDIA_API_KEY"))
    is_ready = database["ok"] and provider_configured
    return JSONResponse(
        status_code=200 if is_ready else 503,
        content={
            "status": "ready" if is_ready else "not_ready",
            "database": database,
            # Configuration only. Checking this makes no paid API call.
            "provider_configured": provider_configured,
        },
    )


@router.get("/config/")
def get_config():
    with connection() as conn:
        settings = settings_repo.load(conn)

    return {
        **_models(),
        "profiles": [profile.as_dict() for profile in config.PROFILES.values()],
        "settings": settings,
        "limits": {
            "max_upload_mb": config.MAX_UPLOAD_BYTES // (1024 * 1024),
            "max_pdf_pages": config.MAX_PDF_PAGES,
            "supported_types": [".pdf", ".txt", ".md"],
            "history_window_messages": config.HISTORY_WINDOW_MESSAGES,
            "settings_ranges": settings_repo.LIMITS,
        },
        "security": {
            "api_token_required": bool(config.API_TOKEN),
            "provider_configured": bool(os.getenv("NVIDIA_API_KEY")),
        },
        "streaming_supported": False,
    }


@router.put("/settings/", response_model=SettingsModel)
def update_settings(body: SettingsUpdate):
    changes = body.model_dump(exclude_none=True)

    with connection() as conn:
        return settings_repo.save(conn, changes)


@router.get("/overview/")
def overview():
    database = _database_status()

    with connection() as conn:
        return {
            "counts": repositories.overview_counts(conn),
            "recent_queries": repositories.recent_queries(conn),
            "recent_jobs": repositories.list_jobs(conn, limit=5),
            "models": _models(),
            "health": {
                "api": True,
                "database": database,
                "provider_configured": bool(os.getenv("NVIDIA_API_KEY")),
            },
        }


@router.get("/metrics/")
def metrics():
    with connection() as conn:
        jobs = repositories.list_jobs(conn, limit=10)

    return {
        **metrics_summary(TRACE_DIR),
        "ingestion_jobs": jobs,
        "not_collected": [
            "Host memory and CPU",
            "Per-endpoint HTTP latency history",
        ],
    }
