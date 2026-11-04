# RAG Evaluation Limitations

1. **One document type.** All numbers come from one resume in 18 chunks. They say little about long, varied or non-technical documents.
2. **Small sample.** With 39 questions and only 6 unanswerable, one question moves a score noticeably. 6 of 6 abstentions is weak evidence.
3. **Judge-based scores.** Faithfulness, relevancy, citation support, coverage and abstention come from an LLM judge, which can be wrong and is not calibrated against human labels here.
4. **The judge is the generator.** The same model wrote and scored the answers, which may raise the scores. This also applies to RAGAS.
5. **Near-identical configurations.** At top 3, configurations B and C gave identical contexts on all 39 questions, and A on 30 of 39. Their generation scores do not show that the retrieval methods are equivalent in general.
6. **The live default was not evaluated end to end.** It reranks 10 candidates, while generation configuration C reranks 18.
7. **The upload path was not evaluated.** Uploads use a generic document prompt and page-aware chunking. The benchmarks used the resume prompt and the existing chunks. Its behaviour was only checked in acceptance tests on a small fictional PDF.
8. **Query expansion is tuned for technical resumes.** Other subjects fall back to plain keywords, so hybrid results may be weaker.
9. **The prompt changed after the generation benchmark.** The evaluated resume prompt later gained a sentence treating context as untrusted. Answers were not regenerated. RAGAS scored the saved answers.
10. **Red-team patterns were tuned on the same attacks,** so those results are counts and not a detection rate.
11. **Annotation corrections are not model improvements.** The 18 corrected instances change scoring only. P013 is unresolved.
12. **Latency came from one machine** and one provider at one time.
