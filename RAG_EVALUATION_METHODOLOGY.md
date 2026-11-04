# RAG Evaluation Methodology

**Dataset.** Golden Dataset V1 has 39 human-reviewed questions, 33 answerable and 6 unanswerable, over chunks 1-18. `golden_dataset_v1.json` is the original and `golden_dataset_v1_reviewed.json` the approved copy.

**Retrieval.** Precision@K, Recall@K and MRR@10 on the 33 answerable questions. Precision divides by the number of results actually returned in the first K ranks.

**Reranking.** Candidate pools are frozen from the retrieval benchmark, then reranked by `nvidia/nemotron-3.5-rerank-8b`. Calls are checkpointed.

**Generation.** The top 3 reranked chunks are given to `nvidia/nemotron-3.5-bolt-e4b`. Top 5 is recorded only as a diagnostic.

These measures are always reported separately:

| Measure | Question it answers | Method |
|---|---|---|
| Faithfulness | Is each factual claim supported by the retrieved context? | LLM judge |
| Citation-ID validity | Does each cited ID exist in the context? | Deterministic |
| Citation support | Does the cited chunk support that particular claim? | LLM judge, exact-set matching |
| Expected-point coverage | Are the reviewed answer points present? | LLM judge |
| Correct abstention | Does it decline when the evidence is absent? | LLM judge |

**RAGAS.** Version 0.4.3 scored the saved answers for configuration C with faithfulness, context recall and context precision. It is an additional view, and it does not replace the measures above.

**Annotation corrections.** Phase 9 reviewed 20 citation failures. These change how particular claims were scored through a separate overlay. Original answers, judge outputs and the dataset stay unchanged, and results stay labelled as corrections.

**Platform replay.** `backend/replay_golden_retrieval.py` reruns the benchmark questions through the platform tables and compares rank lists. It checks that the new code path matches, but it does not produce a new quality result.

**Reproducibility.** Saved reports and checkpoints are hashed. A SHA-256 check of 72 protected files passed before and after this work.
