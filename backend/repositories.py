"""SQL for documents, conversations and dashboard counts."""

from psycopg.types.json import Jsonb

from backend.errors import ApiError, not_found


_DOCUMENT_COLUMNS = (
    "id", "filename", "media_type", "size_bytes", "page_count", "version", "status",
    "error", "chunk_size", "chunk_overlap", "chunk_count", "is_protected",
    "created_at", "updated_at", "indexed_at",
)
_DOCUMENT_SELECT = "SELECT " + ", ".join(_DOCUMENT_COLUMNS) + " FROM source_documents"

_JOB_COLUMNS = (
    "id", "source_document_id", "kind", "status", "filename", "size_bytes",
    "chunk_size", "chunk_overlap", "chunks_created", "error",
    "created_at", "started_at", "finished_at",
)
_JOB_SELECT = "SELECT " + ", ".join(_JOB_COLUMNS) + " FROM ingestion_jobs"


def _row(columns, row):
    return dict(zip(columns, row))


def list_documents(conn):
    rows = conn.execute(_DOCUMENT_SELECT + " ORDER BY updated_at DESC, id DESC")
    return [_row(_DOCUMENT_COLUMNS, row) for row in rows]


def get_document(conn, document_id):
    row = conn.execute(_DOCUMENT_SELECT + " WHERE id = %s", (document_id,)).fetchone()

    if row is None:
        raise not_found("Document")

    return _row(_DOCUMENT_COLUMNS, row)


def list_chunks(conn, document_id, limit, offset):
    rows = conn.execute(
        """
        SELECT id, chunk_index, page_number, content, document_version
        FROM document_chunks WHERE source_document_id = %s
        ORDER BY chunk_index LIMIT %s OFFSET %s
        """,
        (document_id, limit, offset),
    )
    return [
        _row(("id", "chunk_index", "page_number", "content", "document_version"), row)
        for row in rows
    ]


def get_chunk(conn, chunk_id):
    row = conn.execute(
        """
        SELECT c.id, c.chunk_index, c.page_number, c.content, c.document_version,
               c.source_document_id, d.filename
        FROM document_chunks c JOIN source_documents d ON d.id = c.source_document_id
        WHERE c.id = %s
        """,
        (chunk_id,),
    ).fetchone()

    if row is None:
        raise not_found("Chunk")

    return _row(
        ("id", "chunk_index", "page_number", "content", "document_version",
         "document_id", "filename"),
        row,
    )


def list_jobs(conn, document_id=None, limit=20):
    if document_id is None:
        rows = conn.execute(_JOB_SELECT + " ORDER BY id DESC LIMIT %s", (limit,))
    else:
        rows = conn.execute(
            _JOB_SELECT + " WHERE source_document_id = %s ORDER BY id DESC LIMIT %s",
            (document_id, limit),
        )

    return [_row(_JOB_COLUMNS, row) for row in rows]


def delete_document(conn, document_id):
    """Delete a document and its chunks. Returns the stored file path, if any."""

    row = conn.execute(
        "SELECT is_protected, stored_path FROM source_documents WHERE id = %s FOR UPDATE",
        (document_id,),
    ).fetchone()

    if row is None:
        raise not_found("Document")

    if row[0]:
        raise ApiError(
            409, "protected_document",
            "The baseline corpus is needed by the saved benchmarks and cannot be deleted.",
        )

    active = conn.execute(
        "SELECT 1 FROM ingestion_jobs WHERE source_document_id = %s AND status IN ('queued', 'running')",
        (document_id,),
    ).fetchone()

    if active:
        raise ApiError(
            409, "ingestion_in_progress",
            "Wait for processing to finish before deleting this document.",
        )

    conn.execute("DELETE FROM source_documents WHERE id = %s", (document_id,))
    return row[1]


def create_conversation(conn, title="New Conversation"):
    return conn.execute(
        "INSERT INTO conversations (title) VALUES (%s) RETURNING id", (title,)
    ).fetchone()[0]


def conversation_exists(conn, conversation_id):
    return conn.execute(
        "SELECT 1 FROM conversations WHERE id = %s", (conversation_id,)
    ).fetchone() is not None


def load_history(conn, conversation_id, limit):
    rows = conn.execute(
        """
        SELECT role, content FROM conversation_messages
        WHERE conversation_id = %s
        ORDER BY created_at DESC, id DESC LIMIT %s
        """,
        (conversation_id, limit),
    ).fetchall()
    return [{"role": role, "content": content} for role, content in reversed(rows)]


def save_exchange(conn, conversation_id, question, answer, details):
    """Save both messages atomically. The lock keeps concurrent turns in order."""

    conn.execute("SELECT pg_advisory_xact_lock(%s)", (conversation_id,))

    updated = conn.execute(
        """
        UPDATE conversations SET
            updated_at = now(),
            title = CASE WHEN title = 'New Conversation' THEN left(%s, 80) ELSE title END
        WHERE id = %s RETURNING id
        """,
        (question.strip(), conversation_id),
    ).fetchone()

    if updated is None:
        raise not_found("Conversation")

    conn.execute(
        """
        INSERT INTO conversation_messages (conversation_id, role, content)
        VALUES (%s, 'user', %s)
        """,
        (conversation_id, question.strip()),
    )
    message_id = conn.execute(
        """
        INSERT INTO conversation_messages (conversation_id, role, content)
        VALUES (%s, 'assistant', %s) RETURNING id
        """,
        (conversation_id, answer.strip()),
    ).fetchone()[0]
    conn.execute(
        """
        INSERT INTO message_details (
            message_id, status, citations, validation, profile_id, trace_id
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (
            message_id, details["status"], Jsonb(details["citations"]),
            Jsonb(details["validation"]), details["profile_id"], details["trace_id"],
        ),
    )
    return message_id


def list_conversations(conn, limit=50):
    rows = conn.execute(
        """
        SELECT c.id, c.title, c.created_at, c.updated_at, count(m.id)
        FROM conversations c
        LEFT JOIN conversation_messages m ON m.conversation_id = c.id
        GROUP BY c.id
        ORDER BY c.updated_at DESC, c.id DESC LIMIT %s
        """,
        (limit,),
    )
    return [
        _row(("id", "title", "created_at", "updated_at", "message_count"), row)
        for row in rows
    ]


def get_conversation(conn, conversation_id):
    row = conn.execute(
        "SELECT id, title, created_at, updated_at FROM conversations WHERE id = %s",
        (conversation_id,),
    ).fetchone()

    if row is None:
        raise not_found("Conversation")

    conversation = _row(("id", "title", "created_at", "updated_at"), row)
    rows = conn.execute(
        """
        SELECT m.id, m.role, m.content, m.created_at,
               d.status, d.citations, d.validation, d.profile_id, d.trace_id
        FROM conversation_messages m
        LEFT JOIN message_details d ON d.message_id = m.id
        WHERE m.conversation_id = %s
        ORDER BY m.created_at, m.id
        """,
        (conversation_id,),
    )
    conversation["messages"] = [
        _row(
            ("id", "role", "content", "created_at", "status", "citations",
             "validation", "profile_id", "trace_id"),
            message,
        )
        for message in rows
    ]
    return conversation


def delete_conversation(conn, conversation_id):
    deleted = conn.execute(
        "DELETE FROM conversations WHERE id = %s RETURNING id", (conversation_id,)
    ).fetchone()

    if deleted is None:
        raise not_found("Conversation")


def overview_counts(conn):
    row = conn.execute(
        """
        SELECT
            (SELECT count(*) FROM source_documents WHERE status = 'ready'),
            (SELECT count(*) FROM document_chunks),
            (SELECT count(*) FROM conversations),
            (SELECT count(*) FROM conversation_messages WHERE role = 'user')
        """
    ).fetchone()
    return _row(("documents", "chunks", "conversations", "queries"), row)


def recent_queries(conn, limit=8):
    rows = conn.execute(
        """
        SELECT conversation_id, content, created_at FROM conversation_messages
        WHERE role = 'user' ORDER BY created_at DESC, id DESC LIMIT %s
        """,
        (limit,),
    )
    return [_row(("conversation_id", "question", "created_at"), row) for row in rows]
