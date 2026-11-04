"""Runtime settings stored in the database, always validated before use."""

from psycopg.types.json import Jsonb

from backend.config import DEFAULT_SETTINGS, PROFILES
from backend.errors import ApiError


LIMITS = {
    "final_context_k": (1, 10),
    # all-MiniLM-L6-v2 truncates at 256 tokens, so chunks stay below that.
    "chunk_size": (50, 240),
    "chunk_overlap": (0, 100),
}


def validate(settings):
    for name, (low, high) in LIMITS.items():
        value = settings[name]

        if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
            raise ApiError(
                422, "invalid_setting", f"{name} must be between {low} and {high}."
            )

    if settings["chunk_overlap"] >= settings["chunk_size"]:
        raise ApiError(
            422, "invalid_setting", "chunk_overlap must be smaller than chunk_size."
        )

    if settings["default_profile_id"] not in PROFILES:
        raise ApiError(422, "invalid_setting", "Unknown retrieval profile.")

    for name in ("rerank_enabled", "grounding_check"):
        if not isinstance(settings[name], bool):
            raise ApiError(422, "invalid_setting", f"{name} must be true or false.")

    return settings


def load(conn):
    settings = dict(DEFAULT_SETTINGS)

    for key, value in conn.execute("SELECT key, value FROM app_settings"):
        if key in settings:
            settings[key] = value

    return settings


def save(conn, changes):
    settings = validate({**load(conn), **changes})

    for key, value in changes.items():
        conn.execute(
            """
            INSERT INTO app_settings (key, value)
            VALUES (%s, %s)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now()
            """,
            (key, Jsonb(value)),
        )

    return settings
