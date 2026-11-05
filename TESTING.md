# Testing

| Suite | Command | Needs | External calls | Latest result |
|---|---|---|---|---|
| Offline | `scripts/test.sh offline` | Python only | None | 67 passed, 0 failed, 0 skipped |
| Database and API | `RAG_TEST_DB_PORT=5544 scripts/test.sh db` | Disposable PostgreSQL | None, mocked | 37 passed, 0 failed, 0 skipped |
| Frontend | `scripts/test.sh frontend` | Node | None | 33 passed |
| Benchmark replay | `DB_PORT=5544 scripts/test.sh benchmark-replay` | Disposable database with baseline | None | 117 of 117 rank lists match |
| Browser acceptance | `scripts/test.sh e2e` | Live stack | None with the mock provider | 20 of 20 passed with mock provider. 14 of 14 with the live model, before the latest changes |
| External | `scripts/test.sh external` | NVIDIA key | Small live calls | Not part of this run |
| Full evaluations | `evaluate_live_pipeline_depths.py`, `evaluate_ragas.py` | NVIDIA key | Expensive | Not rerun |

On a fresh clone without the private datasets, the suite runs 57 tests and skips 7. It also passes with the network blocked, with 0 connection attempts. Tests for the finished experiments are in `archive/experiment_tests/`.

## Warnings

- **Running the old scripts directly still calls NVIDIA.** `test_nvidia.py` and `test_reranker.py` are scripts. Importing or collecting them makes no connection, but `scripts/test.sh` still lists only real test modules.
- **Integration tests delete conversations and uploaded documents.** They refuse port 5433 for that reason.

## Disposable database

```bash
docker run -d --name rag-test-db -e POSTGRES_DB=rag_db -e POSTGRES_USER=rag_user \
  -e POSTGRES_PASSWORD="$DB_PASSWORD" -p 127.0.0.1:5544:5432 --tmpfs /var/lib/postgresql/data \
  pgvector/pgvector:pg16
PGPASSWORD="$DB_PASSWORD" psql -h localhost -p 5544 -U rag_user -d rag_db -f schema.sql
# Load the baseline, or 18 placeholder rows as in .github/workflows/ci.yml
DB_PORT=5544 venv/bin/python -m backend.migrate
```

## Performance benchmark

`DB_PORT=5544 venv/bin/python -m backend.benchmark_local 5000` measures embedding, insert and retrieval speed with no external calls. Results are in `FINAL_PROJECT_COMPLETION_REPORT.md`.
