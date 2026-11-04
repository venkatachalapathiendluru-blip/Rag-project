-- Additive only. public.documents (the golden benchmark corpus) is never changed.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE source_documents (
    id bigserial PRIMARY KEY,
    filename text NOT NULL,
    media_type text NOT NULL,
    content_sha256 char(64),
    size_bytes bigint,
    page_count integer,
    version integer NOT NULL DEFAULT 0,
    status text NOT NULL DEFAULT 'processing'
        CHECK (status IN ('processing', 'ready', 'failed')),
    error text,
    chunk_size integer,
    chunk_overlap integer,
    chunk_count integer NOT NULL DEFAULT 0,
    stored_path text,
    is_protected boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    indexed_at timestamptz
);

CREATE UNIQUE INDEX source_documents_filename_key ON source_documents (lower(filename));
CREATE UNIQUE INDEX source_documents_sha_key ON source_documents (content_sha256)
    WHERE content_sha256 IS NOT NULL;

-- Uploaded chunks start at 100000, so they can never collide with golden IDs.
CREATE SEQUENCE document_chunks_id_seq START WITH 100000;

CREATE TABLE document_chunks (
    id bigint PRIMARY KEY DEFAULT nextval('document_chunks_id_seq'),
    source_document_id bigint NOT NULL REFERENCES source_documents(id) ON DELETE CASCADE,
    document_version integer NOT NULL,
    chunk_index integer NOT NULL,
    page_number integer,
    content text NOT NULL,
    embedding vector(384) NOT NULL,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (source_document_id, chunk_index)
);

ALTER SEQUENCE document_chunks_id_seq OWNED BY document_chunks.id;

CREATE INDEX document_chunks_source_idx ON document_chunks (source_document_id);
CREATE INDEX document_chunks_fts_idx ON document_chunks
    USING gin (to_tsvector('english', content));

CREATE TABLE ingestion_jobs (
    id bigserial PRIMARY KEY,
    source_document_id bigint NOT NULL REFERENCES source_documents(id) ON DELETE CASCADE,
    kind text NOT NULL CHECK (kind IN ('upload', 'replace', 'reindex')),
    status text NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'running', 'succeeded', 'failed')),
    filename text NOT NULL,
    content_sha256 char(64) NOT NULL,
    size_bytes bigint NOT NULL,
    stored_path text NOT NULL,
    chunk_size integer NOT NULL,
    chunk_overlap integer NOT NULL,
    chunks_created integer,
    error text,
    created_at timestamptz NOT NULL DEFAULT now(),
    started_at timestamptz,
    finished_at timestamptz
);

-- A document can have only one unfinished job at a time.
CREATE UNIQUE INDEX ingestion_jobs_one_active ON ingestion_jobs (source_document_id)
    WHERE status IN ('queued', 'running');

CREATE TABLE message_details (
    message_id bigint PRIMARY KEY REFERENCES conversation_messages(id) ON DELETE CASCADE,
    status text NOT NULL,
    citations jsonb NOT NULL DEFAULT '[]'::jsonb,
    validation jsonb NOT NULL DEFAULT '{}'::jsonb,
    profile_id text,
    trace_id text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE app_settings (
    key text PRIMARY KEY,
    value jsonb NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);
