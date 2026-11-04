# Project Completion Audit (Stage 0)

Audit date: 2026-11-03. Read-only snapshot taken **before** platform work began.
Later progress is tracked in `PROJECT_COMPLETION_CHECKLIST.md` and
`FINAL_PROJECT_COMPLETION_REPORT.md`, so this file stays a record of the starting point.

Classifications: `VERIFIED_COMPLETE`, `PARTIALLY_COMPLETE`, `NOT_IMPLEMENTED`,
`NEEDS_HUMAN_APPROVAL`, `NOT_APPLICABLE`.

## 1. Environment that was actually found

| Item | Found | How it was checked |
|---|---|---|
| Python | 3.10.12 in `venv/` | `venv/bin/python --version` |
| PostgreSQL | 14.24, port 5433 | `select version()` |
| pgvector | 0.8.7 | `pg_extension` |
| `public.documents` | 18 rows, IDs 1-18, `metadata` NULL on all, owned by `postgres` | `psql` |
| `rag_user` rights on `documents` | SELECT/INSERT/UPDATE/DELETE, **not owner, so cannot ALTER** | `role_table_grants` |
| `documents_chunk_test` | 9 rows, chunking experiment | `psql` |
| Conversations | 5 conversations, 18 messages | `psql` |
| Vector index on `documents` | None, so searches are exact scans | `pg_indexes` |
| Node / npm | 24.20.0 / 11.19.0 | `node -v` |
| Docker | Installed. **`docker compose` plugin is not installed** | `docker compose version` |
| Frontend | None. Only the single HTML string in `api.py` | Repository tree |
| Migrations | None | Repository tree |
| CI | None | No `.github/` |
| Git | Initialised in this session, files staged, **no commits and no remote** | `git log`, `git remote` |

## 2. Component classification

| Component | Status | Evidence |
|---|---|---|
| PDF extraction | PARTIALLY_COMPLETE | `rag.py:load_pdf` works, but joins all pages and discards page numbers |
| Token-aware chunking | VERIFIED_COMPLETE | `rag_chat.py:chunk_text`, `test_chunking.py` (script form) |
| Embeddings | VERIFIED_COMPLETE | all-MiniLM-L6-v2, 384 dimensions, normalised |
| pgvector storage | PARTIALLY_COMPLETE | `rag.py:store_embeddings` is transactional but has no document concept |
| Upload, dedupe, versioning, delete, re-index | NOT_IMPLEMENTED | `rag.py --ingest` only appends rows; running it twice duplicates |
| Vector retrieval | VERIFIED_COMPLETE | `rag_chat.py:retrieve_context`, `golden_v1_retrieval_report.json` |
| Keyword retrieval and weighted RRF | VERIFIED_COMPLETE | `hybrid_retriever.py`, `golden_v1_rrf_top18_benchmark.json` |
| Selectable retrieval profiles | NOT_IMPLEMENTED | Values are hard-coded in `rag_chat.py:_run_pipeline` |
| NVIDIA reranking | PARTIALLY_COMPLETE | `rag_chat.py:rerank_context` works and has a timeout, but no retry or backoff, and malformed items raise a bare `KeyError` |
| Grounded generation | PARTIALLY_COMPLETE | `generate_answer` works, but the prompt says "resume assistant" and the result is a bare string |
| Citation-ID validation | VERIFIED_COMPLETE | `validate_citations`, `test_citations.py` |
| Grounding check | PARTIALLY_COMPLETE | `evaluate_grounding` runs, but its verdict is only printed and never reaches an API caller |
| Follow-up rewriting | VERIFIED_COMPLETE | `rewrite_followup_question` |
| Conversation persistence | PARTIALLY_COMPLETE | CLI only, no delete, citations not stored |
| Guardrails, tracing, red team | VERIFIED_COMPLETE | `guardrails.py`, `tracing.py`, `redteam_report.json` (added earlier this session) |
| FastAPI | PARTIALLY_COMPLETE | `api.py` has `/healthz`, `/chat` and a demo page. No `/api/v1` |
| React frontend | NOT_IMPLEMENTED | No `frontend/` |
| Retrieval evaluation | VERIFIED_COMPLETE | Numbers below |
| Reranking evaluation | VERIFIED_COMPLETE | `golden_v1_deep_reranking_report.json` |
| Generation evaluation | VERIFIED_COMPLETE | `golden_v1_generation_report.json` |
| Citation diagnostics, Phase 9 | VERIFIED_COMPLETE | `golden_v1_phase9_citation_report.json`: 18 of 20 instances corrected |
| P013 annotation | **NEEDS_HUMAN_APPROVAL** | `golden_v1_p013_human_review.md`. Not approved, not applied |
| Docker image | PARTIALLY_COMPLETE | Built and tested end to end. `docker-compose.yml` never run with compose |
| Authentication | NOT_IMPLEMENTED | Per-IP rate limit only |
| Multi-user ownership | NOT_APPLICABLE | Single-user local tool. Public use would need it |

## 3. Benchmarks from the brief, checked against the saved reports

Each figure in the brief's Part 3 was compared with the JSON report rather than taken as given.

| Claim | Report | Result |
|---|---|---|
| Retrieval, 4 configurations | `golden_v1_rrf_top18_benchmark.json` | Matches |
| Reranking, 3 configurations | `golden_v1_deep_reranking_report.json` | Matches |
| Generation: faithfulness 1.0, relevancy 4.9697, ID validity 1.0, coverage 0.9535, abstention 6/6 | `golden_v1_generation_report.json` | Matches |
| Citation support micro about 0.81, macro about 0.86 | same | Matches (A 0.8095, B and C 0.8077; macro 0.8611) |
| 18 of 20 corrected, 2 left on P013 | `golden_v1_phase9_citation_report.json` | Matches |

Added since the brief was written: RAGAS on configuration C, with faithfulness 0.9848,
context recall 0.9697, context precision 0.9268 (`ragas_report.json`). The judge is the same model
as the generator.

## 4. Findings the brief did not list

1. **The live pipeline does not match any configuration evaluated end to end.** `_run_pipeline`
   fuses 18 candidates per source, then cuts to `top_k=10` before reranking. The generation
   benchmark's configuration C reranks 18. The closest evaluated match is `rrf_3_1` at depth 10 in
   `golden_v1_reranking_report.json`, which has no generation evaluation.
2. **The default retrieval weighting was changed earlier in this session.** `rag_chat.py` moved from
   RRF 1:1 to 3:1 before the brief arrived, and the user was told at the time. The brief asks that the
   default not change silently, so this is now listed as a decision for the user. A backup of the old
   file exists.
3. **Four files named `test_*.py` are live scripts, not tests.** `test_nvidia.py` calls NVIDIA on
   import. `test_reranker.py`, `test_unseen_retrieval.py` and `test_query_expansion.py` are also scripts
   (`test_unseen_retrieval.py` writes a report). `unittest discover` is therefore unsafe here.
   **During this audit, one `discover` run made one small live NVIDIA chat call.** No artifacts changed.
4. **`documents` cannot be altered by `rag_user`**, and golden chunk IDs 1-18 must stay stable. New
   uploads must therefore not be mixed into that table.
5. **`resume.pdf` and many reports hold personal data.** The allowlist `.gitignore` already keeps them
   out of the repository.
6. **Query expansion in `hybrid_retriever.py` is written for a technical resume.** Other subject
   matter falls back to plain keywords, which will likely score lower than the benchmark suggests.
7. **The working directory has many `.bak` files and old variants** (`rag_chat_before_*.py` and others).
   They are preserved. Cleanup is a user decision.

## 5. Secrets

Searching all project files except `.env`, the virtual environments and `.git` for the live NVIDIA key,
the DB password, and anything shaped like an `nvapi-` key found **no matches**. Nothing was printed.

## 6. Baseline test result

`venv/bin/python -m unittest <15 TestCase modules>`: **183 tests, OK**. `pytest` is not installed.
