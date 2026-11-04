"""Retrieval over the platform tables, using the benchmarked algorithms.

The vector and RRF formulas match golden_v1_rrf_top18_benchmark.py, and
backend/replay_golden_retrieval.py checks that the ranks still agree.
"""

import logging

from hybrid_retriever import build_keyword_query


logger = logging.getLogger("rag.retrieval")

RRF_K = 60

_COLUMNS = """
    c.id, c.content, c.source_document_id, d.filename, c.page_number,
    c.chunk_index, d.version
"""

_READY = "d.status = 'ready' AND (%(document_ids)s::bigint[] IS NULL OR d.id = ANY(%(document_ids)s))"

_VECTOR_SQL = f"""
    SELECT {_COLUMNS}, 1 - (c.embedding <=> %(vector)s::vector) AS similarity
    FROM document_chunks c
    JOIN source_documents d ON d.id = c.source_document_id
    WHERE {_READY}
    ORDER BY c.embedding <=> %(vector)s::vector, c.id
    LIMIT %(depth)s
"""

_RRF_SQL = f"""
    WITH vector_candidates AS (
        SELECT c.id,
               1 - (c.embedding <=> %(vector)s::vector) AS similarity,
               row_number() OVER (ORDER BY c.embedding <=> %(vector)s::vector, c.id) AS vector_rank
        FROM document_chunks c
        JOIN source_documents d ON d.id = c.source_document_id
        WHERE {_READY}
        ORDER BY vector_rank
        LIMIT %(candidate_k)s
    ),
    keyword_candidates AS (
        SELECT c.id,
               row_number() OVER (
                   ORDER BY ts_rank_cd(to_tsvector('english', c.content), q.query) DESC, c.id
               ) AS keyword_rank
        FROM document_chunks c
        JOIN source_documents d ON d.id = c.source_document_id
        CROSS JOIN to_tsquery('english', %(keyword_query)s) AS q(query)
        WHERE {_READY} AND to_tsvector('english', c.content) @@ q.query
        ORDER BY keyword_rank
        LIMIT %(candidate_k)s
    ),
    combined AS (
        SELECT COALESCE(v.id, k.id) AS id,
               COALESCE(v.similarity, 0.0) AS similarity,
               COALESCE(%(vector_weight)s::float / ({RRF_K} + v.vector_rank), 0.0)
               + COALESCE(%(keyword_weight)s::float / ({RRF_K} + k.keyword_rank), 0.0) AS rrf_score
        FROM vector_candidates v
        FULL OUTER JOIN keyword_candidates k ON v.id = k.id
    )
    SELECT {_COLUMNS}, x.similarity
    FROM combined x
    JOIN document_chunks c ON c.id = x.id
    JOIN source_documents d ON d.id = c.source_document_id
    ORDER BY x.rrf_score DESC, x.id
    LIMIT %(depth)s
"""

_FIELDS = (
    "id", "content", "document_id", "filename", "page_number",
    "chunk_index", "document_version", "similarity",
)


def to_vector_literal(embedding):
    return "[" + ",".join(map(str, embedding.tolist())) + "]"


def retrieve(conn, question, embedding_model, profile, document_ids=None):
    """Return ranked chunks for a profile. Hybrid search falls back to vector."""

    if not question or not question.strip():
        return [], "none"

    embedding = embedding_model.encode(
        question, convert_to_numpy=True, normalize_embeddings=True
    )
    params = {
        "vector": to_vector_literal(embedding),
        "depth": profile.depth,
        "candidate_k": profile.candidate_k,
        "document_ids": document_ids or None,
        "vector_weight": profile.vector_weight,
        "keyword_weight": profile.keyword_weight,
        "keyword_query": build_keyword_query(question),
    }

    if profile.mode == "rrf":
        try:
            with conn.transaction():
                rows = conn.execute(_RRF_SQL, params).fetchall()

            return _as_dicts(rows), "hybrid"
        except Exception as error:
            logger.warning(
                "hybrid_retrieval_failed", extra={"error_type": type(error).__name__}
            )

    rows = conn.execute(_VECTOR_SQL, params).fetchall()
    return _as_dicts(rows), ("vector" if profile.mode == "vector" else "vector_fallback")


def _as_dicts(rows):
    return [
        {**dict(zip(_FIELDS, row)), "similarity": float(row[7])}
        for row in rows
    ]
