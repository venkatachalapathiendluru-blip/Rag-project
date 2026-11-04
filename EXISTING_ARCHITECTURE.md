# Existing Architecture (before the platform work)

This describes the system as the Stage 0 audit found it. The current system is in `ARCHITECTURE.md`.

```mermaid
flowchart LR
    PDF[resume.pdf] --> RAG[rag.py: extract, chunk, embed]
    RAG --> DB[(public.documents, 18 chunks)]
    CLI[rag_chat.py CLI] --> RW[Follow-up rewrite]
    RW --> HY[hybrid_retriever.py: vector + keyword + RRF]
    HY --> DB
    HY --> RR[NVIDIA reranker]
    RR --> GEN[NVIDIA generation]
    GEN --> VAL[Citation and grounding checks, printed only]
    VAL --> CONV[(conversations, conversation_messages)]
    DEMO[api.py: /chat, /healthz, HTML page] --> CLI
```

- **Ingestion:** `rag.py --ingest` appends rows. There are no document records, so running it twice duplicates chunks.
- **Evaluation:** separate scripts (`evaluate_golden_v1*.py`, `golden_v1_rrf_top18_benchmark.py`, `diagnose_golden_v1_citation_quality.py`, `apply_golden_v1_phase9_citation_corrections.py`) with checkpoints and JSON or Markdown reports.
- **Golden dataset:** `golden_dataset_v1.json` (original) and `golden_dataset_v1_reviewed.json` (approved).
