"""Connection pool and schema migrations."""

from contextlib import contextmanager
import os
from pathlib import Path
import threading

from psycopg_pool import ConnectionPool

from backend.config import BASE_DIR


MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
BASELINE_FILENAME = "baseline-corpus (golden dataset)"

_pool = None
_pool_lock = threading.Lock()


def _conninfo():
    password = os.getenv("DB_PASSWORD")

    if not password:
        raise RuntimeError("DB_PASSWORD is not set.")

    return {
        "dbname": os.getenv("DB_NAME", "rag_db"),
        "user": os.getenv("DB_USER", "rag_user"),
        "password": password,
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "5433")),
        "connect_timeout": 5,
    }


def get_pool():
    global _pool

    with _pool_lock:
        if _pool is None:
            _pool = ConnectionPool(
                kwargs=_conninfo(),
                min_size=1,
                max_size=int(os.getenv("RAG_DB_POOL_SIZE", "8")),
                timeout=10,
                open=True,
                check=ConnectionPool.check_connection,
            )

    return _pool


def close_pool():
    global _pool

    with _pool_lock:
        if _pool is not None:
            _pool.close()
            _pool = None


@contextmanager
def connection():
    """Yield a pooled connection. It commits on success and rolls back on error."""

    with get_pool().connection() as conn:
        yield conn


def applied_migrations(conn):
    exists = conn.execute(
        "SELECT to_regclass('public.schema_migrations')"
    ).fetchone()[0]

    if not exists:
        return set()

    return {row[0] for row in conn.execute("SELECT name FROM schema_migrations")}


def seed_baseline(conn):
    """Copy the golden corpus into the platform tables with the same chunk IDs.

    public.documents is only read, so benchmarks that use it are unaffected.
    """

    count = conn.execute("SELECT count(*) FROM public.documents").fetchone()[0]
    seeded = conn.execute(
        "SELECT 1 FROM source_documents WHERE is_protected"
    ).fetchone()

    if not count or seeded:
        return 0

    document_id = conn.execute(
        """
        INSERT INTO source_documents (
            filename, media_type, version, status, chunk_count, is_protected, indexed_at
        )
        VALUES (%s, 'application/pdf', 1, 'ready', %s, true, now())
        RETURNING id
        """,
        (BASELINE_FILENAME, count),
    ).fetchone()[0]

    conn.execute(
        """
        INSERT INTO document_chunks (
            id, source_document_id, document_version, chunk_index, content, embedding
        )
        SELECT id, %s, 1, row_number() OVER (ORDER BY id) - 1, content, embedding
        FROM public.documents
        WHERE embedding IS NOT NULL
        ORDER BY id
        """,
        (document_id,),
    )
    return count


def migrate(conn):
    """Apply pending migrations in one transaction and return their names."""

    done = applied_migrations(conn)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            name text PRIMARY KEY,
            applied_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    applied = []

    for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
        if path.name in done:
            continue

        conn.execute(path.read_text(encoding="utf-8"))
        conn.execute("INSERT INTO schema_migrations (name) VALUES (%s)", (path.name,))
        applied.append(path.name)

    seed_baseline(conn)
    return applied


def pending_migrations(conn):
    done = applied_migrations(conn)
    return [
        path.name
        for path in sorted(MIGRATIONS_DIR.glob("*.sql"))
        if path.name not in done
    ]
