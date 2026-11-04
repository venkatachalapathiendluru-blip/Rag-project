# Implementation Roadmap

| Stage | Scope | Status |
|---|---|---|
| 0 | Repository audit | Done |
| 1 | Documentation and evaluation integrity | Done, P013 pending the user |
| 2 | Ingestion and database reliability | Done |
| 3 | Retrieval and reranking reliability | Done |
| 4 | Generation, citations, conversations | Done, except runtime claim-level support |
| 5 | FastAPI backend | Done |
| 6 | React frontend | Done, except streaming and regenerate |
| 7 | Frontend and backend integration | Done |
| 8 | Security and performance review | Done for local use |
| 9 | Docker, deployment, CI | Compose verified. CI has not run |
| 10 | Acceptance tests | 20 of 20 on current code with a mock provider |
| 11 | Final documentation | Done |

## Suggested next steps, most useful first

1. Push to a private GitHub repository so CI runs, and record why grounding checks fail.
2. Evaluate uploaded documents on a second, non-resume dataset with an independent judge.
3. Decide the default retrieval profile, using that new evidence.
4. Add real authentication and document ownership before any public use.
5. Add OCR for scanned PDFs.
6. Add an HNSW index once a corpus is large enough to need it, re-checking recall.
