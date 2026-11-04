# API

Base path: `/api/v1`. Interactive OpenAPI docs are at `/api/v1/docs` on the API port.

When `RAG_API_TOKEN` is set, every route except `health` and `ready` needs `Authorization: Bearer <token>`.

## Errors

Every failure has one shape, and each response has an `X-Request-ID` header.

```json
{"error": {"code": "duplicate_document", "message": "This file is already indexed as guide.pdf.", "details": {"document_id": 3}, "request_id": "..."}}
```

| Status | Codes |
|---|---|
| 401 | `unauthorized` |
| 404 | `not_found` |
| 409 | `duplicate_document`, `protected_document`, `ingestion_in_progress`, `source_file_missing` |
| 413, 415 | `file_too_large`, `unsupported_file_type`, `invalid_pdf`, `invalid_text` |
| 422 | `invalid_request`, `invalid_setting`, `invalid_profile`, `empty_file` |
| 429 | `rate_limited`, `model_rate_limited` |
| 502, 503, 504 | `model_invalid_response`, `model_unavailable`, `database_unavailable`, `model_timeout` |

## Routes

| Method and path | Purpose | Model call? |
|---|---|---|
| `GET /health/` | Is the process up | No |
| `GET /ready/` | Database, migrations, key configured. 503 when not ready | No |
| `GET /config/` | Models, profiles, settings, limits. No secrets | No |
| `PUT /settings/` | Update validated settings | No |
| `GET /overview/` | Counts, recent activity, health | No |
| `GET /metrics/` | Trace summary, errors, ingestion jobs | No |
| `POST /chat/` | Ask a question | Yes |
| `GET /conversations/` | List conversations | No |
| `GET /conversations/{id}` | Messages with citations and validation | No |
| `DELETE /conversations/{id}` | Delete a conversation | No |
| `POST /documents/upload/` | Multipart `file`. Returns 202 and processes in the background | No (embeddings are local) |
| `GET /documents/` | List documents | No |
| `GET /documents/{id}` | Details, jobs, chunks (`chunk_limit`, `chunk_offset`) | No |
| `DELETE /documents/{id}` | Delete a document and its chunks | No |
| `POST /documents/{id}/reindex/` | Rebuild with current chunk settings | No |
| `GET /chunks/{id}` | One chunk with its source | No |
| `GET /evaluations/` | List saved reports with labels | No |
| `GET /evaluations/{id}` | One saved report's summary | No |
| `GET /experiments/comparison/` | Configuration comparison from saved reports | No |

## Chat

```http
POST /api/v1/chat/
{"question": "How often are reports filed?", "conversation_id": 5, "profile_id": "D_rrf3_1_top18", "document_ids": [3]}
```

Only `question` is required. The response includes:

| Field | Meaning |
|---|---|
| `status` | `answered`, `no_evidence_cited`, `no_documents` or `blocked` |
| `answer` | Text with `[Chunk ID: N]` citations |
| `citations` | Only chunks that were cited **and** retrieved, with filename, page, version, text and scores |
| `validation` | Citation-ID result, grounding result, reranker status, retrieval mode, guardrail reasons |
| `trace_id`, `latency_ms`, `profile_id` | Diagnostics |

Streaming is not supported, because the answer is validated and masked before anyone sees it.
