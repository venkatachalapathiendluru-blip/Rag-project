# Deployment

Nothing has been deployed by this work, and no cloud resources were created.

## Local with Docker

```bash
cp .env.example .env   # Fill in NVIDIA_API_KEY and DB_PASSWORD
docker compose up --build
# Open http://127.0.0.1:8080
```

| Service | Image | Notes |
|---|---|---|
| `db` | `pgvector/pgvector:pg16` | Loads `schema.sql` on first start |
| `migrate` | Same image as `api` | Runs `python -m backend.migrate` once and exits |
| `api` | `Dockerfile`, 2.29 GB | Waits for `migrate` and does not migrate by itself. One worker. Peak memory seen with the model loaded was about 1.2 GB |
| `web` | `frontend/Dockerfile`, 95 MB | nginx, static files, `/api` proxy, port 8080 on 127.0.0.1 |

**Tested status:** verified with Compose, including 20 of 20 browser scenarios against a mock provider on a network with no internet access. Details are in `FINAL_PROJECT_COMPLETION_REPORT.md`.

A fresh database starts with no documents. Upload files in the app. To see evaluation dashboards, keep the report files in the folder set by `RAG_REPORTS_HOST_DIR` (default: this folder, mounted read-only). Missing reports show as unavailable.

## Local without Docker, on the existing database

The migration only adds tables and copies the baseline, but it does change the database, so back up first.

```bash
pg_dump -h localhost -p 5433 -U rag_user -d rag_db -Fc -f rag_db_backup_before_migration.dump
venv/bin/pip install -r requirements.txt
venv/bin/python -m backend.migrate
venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8020
```

The backend does not migrate at startup. Until you run this command, `/ready/` returns 503 with `migrations_pending` and data routes return 503. Set `RAG_AUTO_MIGRATE=true` only if you want startup migration. `rag_user` needs permission to create tables in `public`, which it has today.

## Backup and restore

```bash
docker compose exec db pg_dump -U rag_user rag_db > backup.sql
docker compose exec -T db psql -U rag_user rag_db < backup.sql
docker run --rm -v rag_uploads:/data -v "$PWD":/out alpine tar czf /out/uploads.tgz -C /data .
```

The volume name depends on the Compose project name, so check it with `docker volume ls`. A `pg_restore` of the custom-format dump into a separate database has been verified. The Docker commands above have not been run as a restore drill.

## Before any public deployment

Read `SECURITY.md`. The server would also need to fit the 2.29 GB image and about 1.2 GB of memory for the API.
