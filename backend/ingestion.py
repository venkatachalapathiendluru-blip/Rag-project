"""Document ingestion: validate, extract, chunk, embed and swap atomically."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import hashlib
import logging
from pathlib import Path
import re

from psycopg.types.json import Jsonb
from pypdf import PdfReader

from backend import settings_repo
from backend.config import (
    EMBEDDING_DIMENSIONS,
    MAX_PDF_PAGES,
    MAX_UPLOAD_BYTES,
    UPLOAD_DIR,
)
from backend.db import connection
from backend.errors import ApiError


logger = logging.getLogger("rag.ingestion")

SUPPORTED_TYPES = {".pdf": "application/pdf", ".txt": "text/plain", ".md": "text/markdown"}
EMBED_BATCH_SIZE = 32

_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ingestion")


class IngestionError(Exception):
    """A problem with the document, safe to show to the user."""


@dataclass
class Page:
    number: object
    text: str


def safe_filename(name):
    """Keep only a plain base name, so a client cannot choose a path."""

    base = Path((name or "").replace("\\", "/")).name
    base = re.sub(r"[^\w.\- ()]", "_", base).strip(" .")
    return base[:200]


def validate_upload(filename, data):
    """Check name, size and content. Returns (clean_name, media_type)."""

    clean = safe_filename(filename)
    suffix = Path(clean).suffix.lower()

    if not clean or suffix not in SUPPORTED_TYPES:
        allowed = ", ".join(sorted(SUPPORTED_TYPES))
        raise ApiError(415, "unsupported_file_type", f"Supported file types: {allowed}.")

    if not data:
        raise ApiError(422, "empty_file", "The uploaded file is empty.")

    if len(data) > MAX_UPLOAD_BYTES:
        raise ApiError(
            413, "file_too_large",
            f"Files can be up to {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.",
        )

    if suffix == ".pdf":
        if not data.startswith(b"%PDF-"):
            raise ApiError(415, "invalid_pdf", "This file does not contain a valid PDF.")
    else:
        try:
            data.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ApiError(
                415, "invalid_text", "Text files must be UTF-8 encoded."
            ) from error

    return clean, SUPPORTED_TYPES[suffix]


def normalize_text(text):
    text = (text or "").replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t\f\v]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_pages(path, media_type):
    """Return the non-empty pages of a stored file."""

    if media_type != "application/pdf":
        text = normalize_text(Path(path).read_text(encoding="utf-8"))
        pages = [Page(None, text)] if text else []
    else:
        try:
            reader = PdfReader(str(path))

            if reader.is_encrypted:
                raise IngestionError("This PDF is password protected.")

            if len(reader.pages) > MAX_PDF_PAGES:
                raise IngestionError(f"PDFs can have up to {MAX_PDF_PAGES} pages.")

            pages = [
                Page(number, normalize_text(page.extract_text()))
                for number, page in enumerate(reader.pages, start=1)
            ]
        except IngestionError:
            raise
        except Exception as error:
            raise IngestionError("This PDF could not be read.") from error

        pages = [page for page in pages if page.text]

    if not pages:
        raise IngestionError(
            "No text could be extracted. Scanned documents need OCR first."
        )

    return pages


def build_chunks(pages, tokenizer, chunk_text, chunk_size, overlap):
    """Chunk page by page, so that every chunk knows its page number."""

    chunks = []

    for page in pages:
        for content in chunk_text(page.text, tokenizer, chunk_size=chunk_size, overlap=overlap):
            chunks.append({"page_number": page.number, "content": content})

    if not chunks:
        raise IngestionError("The document produced no text chunks.")

    return chunks


def embed_chunks(chunks, model):
    embeddings = model.encode(
        [chunk["content"] for chunk in chunks],
        batch_size=EMBED_BATCH_SIZE,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    if embeddings.ndim != 2 or embeddings.shape != (len(chunks), EMBEDDING_DIMENSIONS):
        raise IngestionError(
            f"Expected {EMBEDDING_DIMENSIONS}-dimensional embeddings, got {embeddings.shape}."
        )

    return embeddings


def store_file(data, sha256, suffix):
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    path = UPLOAD_DIR / f"{sha256}{suffix}"

    if not path.exists():
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_bytes(data)
        temporary.replace(path)

    return path


def create_upload_job(conn, filename, media_type, data):
    """Register an upload: a new document, or a new version of the same filename."""

    sha256 = hashlib.sha256(data).hexdigest()
    settings = settings_repo.load(conn)

    duplicate = conn.execute(
        "SELECT id, filename FROM source_documents WHERE content_sha256 = %s", (sha256,)
    ).fetchone()

    if duplicate:
        raise ApiError(
            409, "duplicate_document",
            f"This file is already indexed as {duplicate[1]}.",
            {"document_id": duplicate[0]},
        )

    existing = conn.execute(
        "SELECT id, is_protected, status FROM source_documents WHERE lower(filename) = lower(%s)",
        (filename,),
    ).fetchone()

    if existing and existing[1]:
        raise ApiError(409, "protected_document", "The baseline corpus cannot be replaced.")

    path = store_file(data, sha256, Path(filename).suffix.lower())

    if existing:
        document_id = existing[0]
        kind = "replace" if existing[2] == "ready" else "upload"
    else:
        document_id = conn.execute(
            """
            INSERT INTO source_documents (filename, media_type, size_bytes)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (filename, media_type, len(data)),
        ).fetchone()[0]
        kind = "upload"

    return _insert_job(conn, document_id, kind, filename, sha256, len(data), path, settings)


def create_reindex_job(conn, document_id):
    row = conn.execute(
        """
        SELECT filename, content_sha256, size_bytes, stored_path, is_protected
        FROM source_documents WHERE id = %s
        """,
        (document_id,),
    ).fetchone()

    if row is None:
        raise ApiError(404, "not_found", "Document was not found.")

    filename, sha256, size_bytes, stored_path, is_protected = row

    if is_protected:
        raise ApiError(
            409, "protected_document",
            "The baseline corpus keeps its benchmarked chunks and cannot be re-indexed.",
        )

    if not stored_path or not Path(stored_path).exists():
        raise ApiError(
            409, "source_file_missing",
            "The original file is no longer stored. Upload it again.",
        )

    return _insert_job(
        conn, document_id, "reindex", filename, sha256, size_bytes,
        stored_path, settings_repo.load(conn),
    )


def _insert_job(conn, document_id, kind, filename, sha256, size_bytes, path, settings):
    active = conn.execute(
        "SELECT id FROM ingestion_jobs WHERE source_document_id = %s AND status IN ('queued', 'running')",
        (document_id,),
    ).fetchone()

    if active:
        raise ApiError(
            409, "ingestion_in_progress",
            "This document is already being processed.", {"job_id": active[0]},
        )

    job_id = conn.execute(
        """
        INSERT INTO ingestion_jobs (
            source_document_id, kind, filename, content_sha256, size_bytes,
            stored_path, chunk_size, chunk_overlap
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """,
        (
            document_id, kind, filename, sha256, size_bytes, str(path),
            settings["chunk_size"], settings["chunk_overlap"],
        ),
    ).fetchone()[0]
    conn.execute(
        """
        UPDATE source_documents SET
            status = CASE WHEN version > 0 THEN status ELSE 'processing' END,
            error = NULL, updated_at = now()
        WHERE id = %s
        """,
        (document_id,),
    )
    return document_id, job_id


def run_job(job_id, get_model, chunk_text):
    """Process one job. Slow work runs outside the final swap transaction."""

    with connection() as conn:
        row = conn.execute(
            """
            UPDATE ingestion_jobs j SET status = 'running', started_at = now()
            FROM source_documents d
            WHERE j.id = %s AND j.status = 'queued' AND d.id = j.source_document_id
            RETURNING j.source_document_id, j.stored_path, j.content_sha256, j.size_bytes,
                      j.chunk_size, j.chunk_overlap, d.media_type
            """,
            (job_id,),
        ).fetchone()

    if row is None:
        return

    document_id, stored_path, sha256, size_bytes, chunk_size, overlap, media_type = row

    try:
        model = get_model()
        pages = extract_pages(stored_path, media_type)
        chunks = build_chunks(pages, model.tokenizer, chunk_text, chunk_size, overlap)
        embeddings = embed_chunks(chunks, model)
    except IngestionError as error:
        _fail_job(job_id, document_id, str(error))
        return
    except Exception as error:
        logger.exception("ingestion_failed", extra={"job_id": job_id})
        _fail_job(job_id, document_id, f"Processing failed ({type(error).__name__}).")
        return

    try:
        replaced_path = _swap_chunks(
            job_id, document_id, sha256, size_bytes, stored_path, media_type,
            chunk_size, overlap, len(pages), chunks, embeddings,
        )

        if replaced_path and replaced_path != stored_path:
            remove_file(replaced_path)
    except Exception as error:
        logger.exception("ingestion_swap_failed", extra={"job_id": job_id})
        _fail_job(job_id, document_id, f"Storing failed ({type(error).__name__}).")


def _swap_chunks(
    job_id, document_id, sha256, size_bytes, stored_path, media_type,
    chunk_size, overlap, page_count, chunks, embeddings,
):
    """Replace old chunks with new ones in one transaction, or change nothing."""

    with connection() as conn:
        current = conn.execute(
            "SELECT version + 1, filename, stored_path FROM source_documents WHERE id = %s FOR UPDATE",
            (document_id,),
        ).fetchone()

        if current is None:
            return None

        version, filename, replaced_path = current
        conn.execute("DELETE FROM document_chunks WHERE source_document_id = %s", (document_id,))

        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO document_chunks (
                    source_document_id, document_version, chunk_index,
                    page_number, content, embedding, metadata
                )
                VALUES (%s, %s, %s, %s, %s, %s::vector, %s)
                """,
                [
                    (
                        document_id, version, index, chunk["page_number"], chunk["content"],
                        "[" + ",".join(map(str, embedding.tolist())) + "]",
                        Jsonb({"filename": filename, "page": chunk["page_number"], "version": version}),
                    )
                    for index, (chunk, embedding) in enumerate(zip(chunks, embeddings))
                ],
            )

        conn.execute(
            """
            UPDATE source_documents SET
                status = 'ready', error = NULL, version = %s, content_sha256 = %s,
                size_bytes = %s, stored_path = %s, media_type = %s, chunk_size = %s,
                chunk_overlap = %s, chunk_count = %s, page_count = %s,
                indexed_at = now(), updated_at = now()
            WHERE id = %s
            """,
            (
                version, sha256, size_bytes, stored_path, media_type, chunk_size,
                overlap, len(chunks), page_count, document_id,
            ),
        )
        conn.execute(
            """
            UPDATE ingestion_jobs
            SET status = 'succeeded', chunks_created = %s, finished_at = now()
            WHERE id = %s
            """,
            (len(chunks), job_id),
        )

    return replaced_path


def remove_file(path):
    """Delete a stored upload, but only inside the upload directory."""

    target = Path(path).resolve()

    if target.parent == UPLOAD_DIR.resolve():
        target.unlink(missing_ok=True)


def _fail_job(job_id, document_id, message):
    """Record a failure. A document with a live version keeps serving it."""

    with connection() as conn:
        stored = conn.execute(
            """
            SELECT j.stored_path, d.stored_path FROM ingestion_jobs j
            JOIN source_documents d ON d.id = j.source_document_id WHERE j.id = %s
            """,
            (job_id,),
        ).fetchone()
        conn.execute(
            """
            UPDATE ingestion_jobs SET status = 'failed', error = %s, finished_at = now()
            WHERE id = %s
            """,
            (message, job_id),
        )
        conn.execute(
            """
            UPDATE source_documents SET
                status = CASE WHEN version > 0 THEN 'ready' ELSE 'failed' END,
                error = %s, updated_at = now()
            WHERE id = %s
            """,
            (message, document_id),
        )

    if stored and stored[0] != stored[1]:
        remove_file(stored[0])


def recover_interrupted_jobs(conn):
    """A restart stops the worker thread, so unfinished jobs are marked failed."""

    rows = conn.execute(
        """
        UPDATE ingestion_jobs
        SET status = 'failed', error = 'Interrupted by a restart. Upload or re-index again.',
            finished_at = now()
        WHERE status IN ('queued', 'running')
        RETURNING source_document_id
        """
    ).fetchall()

    for (document_id,) in rows:
        conn.execute(
            """
            UPDATE source_documents SET
                status = CASE WHEN version > 0 THEN 'ready' ELSE 'failed' END,
                error = 'Interrupted by a restart. Upload or re-index again.',
                updated_at = now()
            WHERE id = %s
            """,
            (document_id,),
        )

    return len(rows)


def submit_job(job_id, get_model, chunk_text):
    _executor.submit(run_job, job_id, get_model, chunk_text)
