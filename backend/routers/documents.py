"""Upload, inspect, re-index and delete documents."""

from fastapi import APIRouter, Depends, File, Query, Request, Response, UploadFile

from backend import config, ingestion, repositories
from backend.chat_service import redact_content
from backend.db import connection
from backend.errors import ApiError
from backend.schemas import Chunk, Document, DocumentDetail, UploadAccepted
from backend.security import client_id, require_token, upload_limiter
from chunking import chunk_text
import rag_chat as engine


router = APIRouter(tags=["documents"], dependencies=[Depends(require_token)])


def _masked(chunks):
    return [{**chunk, "content": redact_content(chunk["content"])} for chunk in chunks]


def _start(job_id):
    ingestion.submit_job(job_id, engine.get_embedding_model, chunk_text)


@router.post("/documents/upload/", response_model=UploadAccepted, status_code=202)
def upload(request: Request, file: UploadFile = File(...)):
    upload_limiter.check(client_id(request))
    data = file.file.read(config.MAX_UPLOAD_BYTES + 1)
    filename, media_type = ingestion.validate_upload(file.filename, data)

    with connection() as conn:
        document_id, job_id = ingestion.create_upload_job(conn, filename, media_type, data)

    _start(job_id)
    return {"document_id": document_id, "job_id": job_id}


@router.get("/documents/", response_model=list[Document])
def list_documents():
    with connection() as conn:
        return repositories.list_documents(conn)


@router.get("/documents/{document_id}", response_model=DocumentDetail)
def get_document(
    document_id: int,
    chunk_limit: int = Query(default=50, ge=1, le=200),
    chunk_offset: int = Query(default=0, ge=0),
):
    with connection() as conn:
        document = repositories.get_document(conn, document_id)
        document["jobs"] = repositories.list_jobs(conn, document_id)
        document["chunks"] = _masked(
            repositories.list_chunks(conn, document_id, chunk_limit, chunk_offset)
        )

    return document


@router.get("/chunks/{chunk_id}")
def get_chunk(chunk_id: int):
    with connection() as conn:
        return _masked([repositories.get_chunk(conn, chunk_id)])[0]


@router.delete("/documents/{document_id}", status_code=204)
def delete_document(document_id: int):
    with connection() as conn:
        stored_path = repositories.delete_document(conn, document_id)

    if stored_path:
        ingestion.remove_file(stored_path)

    return Response(status_code=204)


@router.post("/documents/{document_id}/reindex/", response_model=UploadAccepted, status_code=202)
def reindex(document_id: int):
    with connection() as conn:
        document_id, job_id = ingestion.create_reindex_job(conn, document_id)

    _start(job_id)
    return {"document_id": document_id, "job_id": job_id}
