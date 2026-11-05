# Final Project Completion Report

Date: 2026-11-03. **Maturity: C, integrated full-stack application.** Not production-ready.

## Final integration verification

Run on 2026-11-03 against the current code. "Mock" means a local stand-in for NVIDIA: it tests the application around the model, not model quality.

### Browser tests after the latest changes

**20 of 20 passed: the original 14 plus 6 new ones, all with the mock provider.** They ran in a separate Compose project (`ragverify`) with its own database, on a network with no internet access. The API could not reach NVIDIA (DNS failure confirmed from inside the container), and the mock received 21 chat and 11 rerank calls. That project has since been removed.

| Group | Scenarios |
|---|---|
| Original 14 | Upload and ingestion, grounded answer flow, citation evidence, refresh persistence, follow-up, abstention flow, injection block, evaluation dashboard, experiments, invalid upload and API outage, secret check, responsive and dark, delete, console errors |
| New 6 | All eight pages render. A missing page number shows "Not recorded". A model failure shows a safe error with no provider detail. A reranker failure degrades visibly. Grounding passed and failed verdicts both appear. Database outage and recovery |

**Database outage:** with the database stopped, `health` stayed 200, `ready` returned 503, and Documents and Chat showed a safe error. After restart the API recovered by itself with data intact.

**What these do not prove:** the answers, abstention and follow-up rewriting are scripted. The last browser run with the real model was before these changes. Since then, real-model checks have been at API level only (below).

### Docker Compose evidence

| Check | Running `rag` project | Disposable `ragverify` project |
|---|---|---|
| Started by | Not started by this work. Created 22:41 IST. Who started it was not established | This work |
| `migrate` | Exited 0, applied `001_platform.sql` | Exited 0 |
| `db`, `api`, `web` | Healthy, 0 restarts | Healthy |
| Published ports | Only `127.0.0.1:8080` | Only `127.0.0.1:8090` |
| Database | Own volume `rag_pgdata`, no published port, `DB_HOST=db` | Removed afterwards |
| Error lines in logs | API 0, web 0 | No tracebacks, no secrets, no provider detail |
| `/ready/` | 200 | 200 |

**The running stack is isolated from `rag_db`:** it connects to its own `db` container, and `rag_db` shows no change (next section). It was inspected only: never stopped, restarted or recreated, and its start times did not change.

**It predates the latest code.** Its API image was built at 22:40, before the new report was registered and the evaluation page changed. The browser tests ran on the newer code. A rebuild is needed to pick those up, and that is left to its owner.

**Defect fixed:** the one-time `migrate` container inherited the image's health check, so it was marked unhealthy after a clean exit. `docker-compose.yml` now disables that check for `migrate`. This takes effect the next time the stack is recreated.

### Migration status

| Check | Result |
|---|---|
| `rag_db` migrated? | **No.** No platform tables, still 4 tables, 18 documents, 5 conversations, 18 messages. `documents` fingerprint unchanged |
| Backup | `rag_db_backup_before_migration.dump`, 70 KB, readable, git-ignored |
| Restore | Restored into a separate PostgreSQL 14 copy with `documents` owned by `postgres` and a non-superuser `rag_user`. Fingerprint and row counts match |
| Migration on that copy | Applied once, then "nothing to do" on two later runs. Existing tables unchanged, 18 of 18 baseline chunks identical, 117 of 117 rank lists match |
| Separate step in Docker | Yes, the `migrate` service runs once and the API waits for it |
| API startup | Does not migrate unless `RAG_AUTO_MIGRATE=true`. Verified on an unmigrated database: no tables added, `ready` returned 503 with `migrations_pending`, and a test covers it |

### Latency, six live questions

Measured from traces, through the real API on the copy of the baseline corpus, with real NVIDIA calls. The first turn is excluded because it loads the embedding model. With only 5 turns, the last column is the maximum and not a p95.

| Stage | p50 | Max |
|---|---|---|
| Retrieval | 18 ms | 26 ms |
| Reranker | 437 ms | 496 ms |
| Generation | 13.6 s | 16.4 s |
| Grounding check | 22.5 s | 95.5 s |
| **Total response** | **39.4 s** | **111.5 s** |

- **These are pessimistic.** The depth comparison was using the same provider at the same time. An earlier run with no parallel load and a much smaller corpus had a p50 of 9.5 s, with generation at 3.5 s and grounding at 5.5 s. The two causes can't be separated from this data.
- **Grounding is 63.5% of the median response,** and it runs before the user sees anything.
- **One of six grounding checks failed:** it took 95.5 s and returned `NOT_VALIDATED`. The answer was still returned, marked "Grounding check unavailable". The cause is not known, because the failure reason is not saved in the trace or logs. That is worth fixing.
- **The timing change works:** `retrieval` now appears in traces and on the metrics endpoint.

The grounding check was not changed or disabled.

**If grounding were disabled:**

- **Quality:** users lose the per-answer check that the answer's claims are supported by the retrieved text. Citation-ID validation stays, but it only proves a cited chunk exists, not that it supports the claim. Offline, citation support was 0.81 even with ID validity at 1.0, so this gap is real.
- **Security:** it is not a security boundary, so the injection patterns, chunk sanitising, hardened prompt and output masking would all keep working. But an attack that slips through and produces an unsupported answer would lose its one runtime warning.
- **It warns but does not block.** Today a failed answer is still shown, with a badge. Disabling it removes that warning, and it does not remove any blocking.
- **Limits of the check:** its judge is the same model as the generator, and it has not been calibrated against human labels.
- **Option to consider, not implemented:** show the answer first and run the check in the background. This keeps the signal without the wait, but users could read an answer before its warning arrives.

### Test isolation

**The claim was false, and is now fixed.** With sockets blocked, importing `test_nvidia.py` tried to reach `integrate.api.nvidia.com` 3 times. It, `test_unseen_retrieval.py` and `test_query_expansion.py` now run only when executed directly.

| Check, network blocked | Result |
|---|---|
| Import `test_nvidia`, `test_reranker`, `test_chunking`, `test_query_expansion`, `test_unseen_retrieval` | 0 connection attempts each |
| `unittest` discovery across all `test_*.py` | 262 tests collected, 0 connection attempts, no report rewritten |
| Full offline suite | 225 passed, 0 failed, 0 skipped, 0 connection attempts |

A new test keeps the `test_nvidia` import offline.

### Current test totals

| Suite | Result |
|---|---|
| Offline Python | 225 passed |
| Database and API, mocked model | 37 passed |
| Frontend components | 33 passed |
| Browser, mock provider | 20 of 20 passed |
| Protected files | 72 of 72 hashes match |

### Current default

**Nothing is in production.** The application default is `rrf3_1_top10` (RRF 3:1, rerank top 10), labelled provisional and experimental. It has not changed.

The missing depth 10 and 18 comparison (`evaluate_live_pipeline_depths.py`) **was still running when this was written, so it has no results here.** No winner can be declared from it anyway, because a second independent dataset is still needed.

### GitHub readiness

**Ready for a private repository once you review it. Not yet ready to be public.** Nothing is committed or pushed, and there is no remote.

| Item | Finding |
|---|---|
| File count | 124 staged |
| Compared with the audit-time backup | 100 new, 8 modified, 16 unchanged |
| Modified | `.dockerignore`, `.env.example`, `.gitignore`, `Dockerfile`, `docker-compose.yml`, `rag.py`, `rag_chat.py`, `requirements.txt` |
| New | `frontend/` 50, `backend/` 23, `tests/` 5, plus documentation, `chunking.py`, the comparison script, the CI workflow and the test runner |
| Live key, database password | 0 matches |
| Other key formats, private keys | None, except clearly fake `nvapi-` values in `test_guardrails.py` and `tests/test_platform_integration.py`, used to test masking |
| Phone, email, your name, your home folder path | 0 matches |
| **Resume-derived data** | **`golden_dataset_v1_reviewed.json` only.** It contains your employer, college, degree, city and work history in question form. **It is the one blocker to going public** |
| Generated reports staged | `ragas_report.json` and `redteam_report.json`. Scores and attack results only; neither contains the employer or college names searched for |
| Backups, dumps, documents | None staged. The dump, `.env`, `resume.pdf`, uploads, traces and checkpoints are git-ignored. 31 older backup or variant files stay on disk, unstaged |
| Whitespace | A harmless extra blank line at the end of `hybrid_retriever.py` and `schema.sql` |

**A fresh clone would not reproduce the headline numbers.** Most evaluation reports are git-ignored, so its dashboards would show them as unavailable, and it would have no resume corpus to rerun on. Publishing a sanitised corpus and reports would fix this for a public version.

The public or private decision remains yours.

## 1. Executive summary

The command-line RAG system is now a working web application. A user can upload a document, ask about it, open the exact source text behind a citation, return to the conversation later, and inspect saved evaluation results. All of it was tested in real Chrome: 14 of 14 scenarios passed on containers with live NVIDIA calls, then 20 of 20 with a mock provider after the latest changes.

Three things remain open: CI has never run, the live default configuration has no finished end-to-end generation evaluation, and the P013 and default-profile decisions belong to the user. `docker compose up` has now been verified, as described above.

Weighted completion is **about 90%** (section 22). That number reflects judgement applied to the evidence, and is not a measurement.

## 2. Original project goal

A professional full-stack RAG application with real ingestion, hybrid retrieval, reranking, grounded answers, citations, conversations, abstention, and an evaluation dashboard, with no fabricated metrics.

## 3. Initial repository state

In short: strong evaluation work and a CLI pipeline, a one-page demo API, no document management, no frontend, no migrations and no CI.

## 4. Verified completed work kept as it was

Golden dataset, all benchmarks and checkpoints, Phase 9 corrections, RAGAS, the red team, guardrails and tracing. Every figure in the brief matched its saved report.

## 5. New functionality

- Document lifecycle: upload, duplicate detection, versioned replacement, re-index, delete, restart recovery.
- `/api/v1` backend with connection pooling, one error shape, request IDs and JSON logs.
- Retrieval profiles selectable without source edits.
- Structured chat results, with citations and validation saved per message.
- Reranker retries with backoff, and clear handling of malformed responses.
- React application with eight pages.
- Separate frontend image, nginx proxy, CI workflow, test runner and benchmark.

## 6. Frontend

See `FRONTEND_ARCHITECTURE.md`. Pages: Overview, AI Chat, Documents, Conversations, Evaluation, Retrieval Experiments, System Monitoring, Settings. Not implemented: streaming and regenerate. `components/ui` follows the shadcn/ui pattern but was written by hand.

## 7. Backend

See `API_DOCUMENTATION.md`. Handlers are sync functions, so FastAPI runs them in a thread pool and they do not block the event loop. Ingestion uses one in-process worker thread rather than a job system: it is enough for one local user, but it requires a single API process.

## 8. Database

Migration `001_platform.sql` only adds tables. **It has not been applied to your `rag_db`.** All testing used disposable containers. After this work `rag_db` still has 18 documents, 5 conversations and no platform tables. See `DEPLOYMENT.md` for the command. Starting the backend no longer applies it.

## 9. RAG architecture

See `ARCHITECTURE.md`.

## 10. Retrieval and reranking findings

- RRF 3:1 has the best MRR@10 before reranking (0.9571), but vector search keeps better R@5 and R@10.
- After reranking at depth 18, vector and RRF 3:1 score the same.
- **The live pipeline matches no configuration in the generation benchmark.** It reranks 10 candidates. Configuration C reranks 18.

## 11. Generation and citation evaluation

See `RAG_FINAL_EVALUATION_REPORT.md`. Faithfulness 1.0, citation-ID validity 1.0, citation support 0.81 micro and 0.86 macro, abstention 6 of 6, all from a judge that is also the generator.

## 12. Original versus corrected results

| | Original | After offline annotation |
|---|---|---|
| The 20 reviewed failure instances | 20 unsupported | 18 supported, 2 unsupported |
| Answers, judge outputs, dataset | Unchanged | Unchanged |
| Model quality | No change | No change |

No overall corrected citation-support score is presented, and the dashboard labels this as a correction.

## 13. P013 status

**NEEDS_HUMAN_APPROVAL.** Recommendation: approve chunk 13 for both instances. Not applied.

## 14. File changes

**New:** `backend/` (config, db, migrate, migrations, errors, schemas, security, telemetry, settings_repo, repositories, retrieval, ingestion, chat_service, reports, main, routers, replay_golden_retrieval, benchmark_local), `chunking.py`, `tests/`, `frontend/`, `scripts/test.sh`, `.github/workflows/ci.yml`, `PRODUCT.md` and the documentation set.

**Changed:**

| File | Change |
|---|---|
| `rag_chat.py` | Env-configurable RRF weights (same defaults), reranker retries and validation, optional `system_prompt`, grounding token usage now recorded |
| `rag.py` | `chunk_text` moved to `chunking.py`, unchanged |
| `Dockerfile`, `docker-compose.yml`, `requirements.txt`, `.gitignore`, `.dockerignore`, `.env.example` | Updated for the platform |

**Not changed:** all 72 hashed reports, checkpoints, datasets and backups. The old `api.py` was later removed.

## 15. Test results

| Suite | Result |
|---|---|
| Offline Python | 225 passed, 0 failed, 0 skipped |
| Database and API, mocked model | 37 passed, 0 failed, 0 skipped |
| Frontend components | 33 passed, 0 failed |
| Benchmark replay | 117 of 117 rank lists match |
| Browser, on containers, live model, before the latest changes | 14 of 14 passed |
| Browser, on Compose, mock provider, current code | 20 of 20 passed |
| Live database outage | Health 200, ready and data routes 503 with the safe error |

Mocked tests cover timeouts, rate limits, malformed replies and provider errors. Those failures were not provoked against the real provider.

## 16. Build results

Type check passed. Production build passed, with the main chunk at 665 kB (208 kB gzipped), above Vite's 500 kB advice. Lint gave 2 style warnings. Images: API 2.29 GB, web 95 MB.

## 17. Security review

See `SECURITY.md`. Suitable for one local user. `npm audit` reported 0 vulnerabilities. Python dependencies were not scanned. No credentials were found in project files.

## 18. Performance findings

Measured on this machine, with one provider, at one time.

**A chat turn** (4 answered turns on the small test corpus): p50 9.5 s, p95 14.0 s.

| Stage | p50 | p95 |
|---|---|---|
| Rerank | 0.43 s | 1.06 s |
| Generate | 3.45 s | 3.83 s |
| Grounding check | 5.51 s | 6.14 s |

**The grounding check is the largest single stage,** which makes it the first thing to look at for speed. It can be switched off in Settings, at the cost of that check.

| Local measure (`backend.benchmark_local`, 5,000 chunks) | Result |
|---|---|
| Embedding | 498 chunks/s |
| Database insert | 2,434 chunks/s |
| Vector retrieval, including query embedding | p50 17 ms, p95 22 ms |
| RRF 3:1 retrieval, including query embedding | p50 30 ms, p95 124 ms |
| 8 concurrent workers, RRF | 53 requests/s |
| 300-page PDF, 1,500 chunks, through the real pipeline | 50 s |
| API process memory after that | About 1.2 GB |

No cache or vector index was added, because retrieval is not the bottleneck at this size. Without an index, search stays exact, which also keeps the benchmarks valid.

## 19. Docker and deployment

Both images built. `docker compose up` is verified on a running stack and on a disposable project, as described above. Earlier, the permission system blocked downloading a compose binary; the plugin was later installed outside this work. Nothing was deployed.

## 20. Known limitations

1. The live default and the upload path have no end-to-end generation evaluation.
2. Upload answers use a new generic prompt that the benchmarks did not measure.
3. Query expansion is tuned for technical resumes.
4. Scanned PDFs are rejected with a clear message, because there is no OCR.
5. No streaming, regenerate or runtime claim-level citation support.
6. One shared token instead of user accounts.
7. One API process only, because of the in-process worker.
8. CI has never run. The `pg_restore` path is proven, but the Docker volume backup commands have not been run.
9. Monitoring does not collect host metrics or per-endpoint latency history.
10. The local database is PostgreSQL 14, while containers use 16. The benchmark replay matched on 16.

**Outstanding security gaps**

- The running stack has no API token set. It relies on binding to `127.0.0.1`.
- There are no user accounts or per-user data, only an optional shared token.
- There is no TLS.
- The default reports mount exposes the whole project folder to the API container read-only. That includes `.env`, the database dump and `resume.pdf`. The app reads only registered report files, but a compromised API could read them all. Point `RAG_REPORTS_HOST_DIR` at a dedicated folder.
- Rate limits are in memory.
- Uploaded files are stored unencrypted.
- Python dependencies have not been scanned.
- Injection patterns were tuned on the same cases they were tested on.
- A failed grounding check warns but does not block, and its failure reason is not recorded.

## 21. Outstanding human decisions

| Decision | Recommendation |
|---|---|
| **P013:** approve chunk 13 for both instances? | Approve, per the review file. It would add a new labelled result, not change the originals |
| **Default retrieval profile:** keep RRF 3:1 at depth 10? It was changed from 1:1 earlier in this session, before the brief, and you were told then | Keep it for now. Consider `B_vector_top18`, which is simpler and scored the same after reranking |
| **Apply the migration to `rag_db`?** | Backup and test are done. Run it when you want the app on your data |
| **Rebuild the running stack?** It predates the latest code | Rebuild when convenient |
| **Remove resume-derived data before any public release?** | Yes, if the repository goes public |
| **Private or public GitHub repository?** Files are staged, with no commit or remote | Pending. Private first, as you suggested |
| **Clean up old `.bak` and variant files?** | Optional. Preserved for now |

## 22. Commands and completion

```bash
# Docker
cp .env.example .env && docker compose up --build    # http://127.0.0.1:8080

# Without Docker, against rag_db. Back up first, and apply the migration on purpose.
venv/bin/python -m backend.migrate
venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8020
cd frontend && npm ci && npm run dev                 # http://127.0.0.1:5173

# Tests
scripts/test.sh offline
```

| Category | Weight | Assessed | Points | Main gap |
|---|---|---:|---:|---|
| Core RAG and ingestion | 20% | 95% | 19.0 | No OCR |
| Retrieval, reranking, generation | 15% | 90% | 13.5 | No runtime claim-level support, new prompt unmeasured |
| Evaluation and reproducibility | 15% | 90% | 13.5 | P013 open, live default not evaluated end to end |
| Backend and API | 15% | 95% | 14.25 | Light dependency injection |
| Frontend | 15% | 90% | 13.5 | No streaming or regenerate |
| Security and reliability | 10% | 70% | 7.0 | Shared token only, Python packages not scanned |
| Testing, deployment, documentation | 10% | 92% | 9.2 | CI has not run |
| **Total** | | | **89.95** | |

**Maturity: C.** It is more than a local prototype because every feature runs through real APIs and a real browser. It is not D, because it lacks user accounts, a CI run, TLS, operational monitoring and evaluation on varied documents. The evidence does not support calling it production-ready.

## 23. Recommended future enhancements

1. Push to a private GitHub repository so CI runs, and record why grounding checks fail.
2. Evaluate uploaded documents on a second, non-resume dataset with an independent judge.
3. Decide the default retrieval profile, using that new evidence.
4. Add real authentication and document ownership before any public use.
5. Add OCR for scanned PDFs.
6. Add an HNSW index once a corpus is large enough to need it, re-checking recall.

## Disclosures

- **Live API use:** one unplanned small chat call when `unittest discover` imported `test_nvidia.py` during the audit; three browser runs of about four answered questions each, roughly 40 calls in total; six live questions for latency, about 18 calls; and the depth comparison, 132 planned calls and about 160k estimated tokens. No earlier evaluation was repeated.
- **Permission block:** downloading the compose binary was denied, and this was not worked around.
- **Design step skipped:** the design skill calls for an interview. `PRODUCT.md` was inferred from the brief instead, with its assumptions marked.
