# RAG Final Evaluation Report

All figures are read from saved reports. No evaluation was rerun for this report. Read it alongside `RAG_EVALUATION_LIMITATIONS.md`.

## Retrieval, candidate pool 18 (original evaluation)

| Configuration | P@3 | P@5 | P@10 | R@3 | R@5 | R@10 | MRR@10 |
|---|---|---|---|---|---|---|---|
| Vector | 0.4646 | 0.3273 | 0.1818 | 0.7879 | 0.9192 | 0.9823 | 0.9010 |
| Keyword | 0.3838 | 0.3111 | 0.2498 | 0.6667 | 0.8030 | 0.8965 | 0.6541 |
| RRF 1:1 | 0.4242 | 0.3091 | 0.1727 | 0.7727 | 0.8788 | 0.9419 | 0.7955 |
| RRF 2:1 | 0.4343 | 0.3212 | 0.1788 | 0.7702 | 0.9040 | 0.9672 | 0.9091 |
| RRF 3:1 | 0.4646 | 0.3212 | 0.1788 | 0.7980 | 0.9040 | 0.9672 | 0.9571 |

RRF 3:1 has the best MRR@10 and R@3 here, but vector search has better R@5 and R@10, so 3:1 does not win at every cutoff. RRF 1:1 trails vector search.

## Reranking (original evaluation)

| Configuration | P@3 | P@5 | R@3 | R@5 | MRR@10 |
|---|---|---|---|---|---|
| Vector top 10 | 0.4646 → 0.5354 | 0.3273 → 0.3394 | 0.7879 → 0.9040 | 0.9192 → 0.9394 | 0.9010 → 0.9697 |
| Vector top 18 | 0.4646 → 0.5455 | 0.3273 → 0.3455 | 0.7879 → 0.9141 | 0.9192 → 0.9495 | 0.9010 → 0.9697 |
| RRF 3:1 top 18 | 0.4646 → 0.5455 | 0.3212 → 0.3455 | 0.7980 → 0.9141 | 0.9040 → 0.9495 | 0.9571 → 0.9697 |

After reranking, vector top 18 and RRF 3:1 top 18 score the same on every metric in this table. The dataset does not separate them.

The current default, RRF 3:1 reranked at depth 10, reached R@3 0.8990, R@5 0.9242 and MRR@10 0.9697 in `golden_v1_reranking_report.json`.

## Generation, top 3 context (original evaluation, LLM judge)

| Measure | A: vector 10 | B: vector 18 | C: RRF 3:1, 18 |
|---|---|---|---|
| Faithfulness, micro and macro | 1.0 | 1.0 | 1.0 |
| Answer relevancy (1 to 5) | 4.9697 | 4.9697 | 4.9697 |
| Citation-ID validity | 1.0 | 1.0 | 1.0 |
| Citation support, micro | 0.8095 | 0.8077 | 0.8077 |
| Citation support, macro | 0.8611 | 0.8611 | 0.8611 |
| Expected-point coverage, micro | 0.9535 | 0.9535 | 0.9535 |
| Correct abstention | 6/6 | 6/6 | 6/6 |

Across the runs this used 168,603 tokens, reconstructed in part from saved stage signatures. One recovered failure has no usage data, so the true total is slightly higher.

## Citation annotation corrections (offline, not a model improvement)

| Item | Count |
|---|---|
| Failure instances reviewed | 20 |
| Corrected by annotation | 18 |
| Still unsupported | 2 |

## P013 status: NEEDS_HUMAN_APPROVAL

Two instances on GDV1-026 remain unresolved. `golden_v1_p013_human_review.md` recommends approving chunk 13 for both, but the user has not approved that. It has not been applied, and no human-approved results exist.

## RAGAS (new evaluation, configuration C, 33 questions)

| Metric | Mean |
|---|---|
| Faithfulness | 0.9848 |
| Context recall | 0.9697 |
| Context precision | 0.9268 |

RAGAS faithfulness (0.9848) is a little lower than the original judge's 1.0. They use different methods, so neither figure replaces the other.

## Prompt injection red team (new evaluation)

24 of 24 direct attacks blocked. 0 of 15 normal questions blocked. All 39 golden questions pass the input check. 0 of 6 indirect attacks succeeded, both with the prompt alone and with the sanitizer.

## Decision guidance

The data does not support declaring one configuration best. RRF 3:1 helps before reranking, and that advantage disappears after reranking at depth 18. Vector top 18 is the simpler option with the same reranked scores. A larger, more varied dataset is needed to decide.
