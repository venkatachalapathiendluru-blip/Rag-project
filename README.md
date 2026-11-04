# Enterprise RAG Platform

Upload documents, ask questions, and check the exact source text behind each answer. Retrieval quality, citations and abstention are measured against a human-reviewed golden dataset, and the results are shown in the app with their limits.

**Stack:** FastAPI, PostgreSQL with pgvector, all-MiniLM-L6-v2 embeddings, NVIDIA-hosted generation and reranking, React, TypeScript, Vite, Tailwind CSS.

## What it does

- Uploads PDF, TXT and Markdown files, with duplicate detection, versioned replacement, re-indexing and deletion.
- Retrieves with vector search and weighted Reciprocal Rank Fusion, selectable by profile, then reranks with NVIDIA.
- Answers with citations. Selecting a citation shows the document, page and actual chunk text.
- Keeps multi-turn conversations in PostgreSQL, including their citations.
- Blocks prompt injection, masks sensitive values and traces each request with stage timings and token counts.
- Shows saved evaluation results without running anything or calling a model.

## Measured results

From saved reports on one 18-chunk resume corpus with 39 questions (33 answerable, 6 unanswerable). They describe this dataset, not general performance. Details are in [RAG_FINAL_EVALUATION_REPORT.md](RAG_FINAL_EVALUATION_REPORT.md) and [RAG_EVALUATION_LIMITATIONS.md](RAG_EVALUATION_LIMITATIONS.md).

| Measure | Result |
|---|---|
| MRR@10, RRF 3:1 before and after reranking (top 18) | 0.9571, then 0.9697 |
| Recall@3, RRF 3:1 before and after reranking (top 18) | 0.7980, then 0.9141 |
| Citation-ID validity, LLM-free check | 1.0 |
| Claim citation support, LLM judge, original scoring | 0.81 micro, 0.86 macro |
| Correct abstention, LLM judge | 6 of 6 |
| RAGAS faithfulness, context recall, context precision | 0.9848, 0.9697, 0.9268 |
| Prompt injection red team | 24 of 24 direct attacks blocked, 0 of 15 normal questions blocked |

The judge is the same model as the generator, and the attack patterns were tuned on the same cases, so the red-team figures are counts rather than a detection rate.

## Run it

Requires Docker with the Compose plugin, and an NVIDIA API key.

```bash
cp .env.example .env     # Fill in NVIDIA_API_KEY and DB_PASSWORD
docker compose up --build
```

Open http://127.0.0.1:8080. For local development without Docker, see [FRONTEND_SETUP.md](FRONTEND_SETUP.md) and [DEPLOYMENT.md](DEPLOYMENT.md).

Migrations are a separate step: Compose runs them once before the API starts. Outside Docker, run `python -m backend.migrate`.

## Tests

```bash
scripts/test.sh offline     # No database, network or model
scripts/test.sh db          # Disposable database, mocked model APIs
scripts/test.sh frontend    # Types, component tests, production build
```

See [TESTING.md](TESTING.md).

## Documentation

[Architecture](ARCHITECTURE.md) · [API](API_DOCUMENTATION.md) · [Security](SECURITY.md) · [Deployment](DEPLOYMENT.md) · [Evaluation methodology](RAG_EVALUATION_METHODOLOGY.md) · [Frontend architecture](FRONTEND_ARCHITECTURE.md) · [Completion report](FINAL_PROJECT_COMPLETION_REPORT.md)
