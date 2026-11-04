"""Read saved evaluation reports. Nothing here calls a model or changes a file.

Results keep the label of the evaluation that produced them, so original runs,
annotation corrections and new runs are never presented as one series.
"""

import json
from pathlib import Path
import statistics

from backend import config
from backend.errors import not_found


REGISTRY = {
    "retrieval_top18": {
        "file": "golden_v1_rrf_top18_benchmark.json",
        "title": "Retrieval benchmark, candidate pool 18",
        "category": "retrieval",
        "label": "ORIGINAL_EVALUATION",
    },
    "reranking_top10": {
        "file": "golden_v1_reranking_report.json",
        "title": "Reranking at depth 10",
        "category": "reranking",
        "label": "ORIGINAL_EVALUATION",
    },
    "reranking_deep": {
        "file": "golden_v1_deep_reranking_report.json",
        "title": "Reranking at depths 10 and 18",
        "category": "reranking",
        "label": "ORIGINAL_EVALUATION",
    },
    "generation": {
        "file": "golden_v1_generation_report.json",
        "title": "Generation and abstention, LLM judge",
        "category": "generation",
        "label": "ORIGINAL_EVALUATION",
    },
    "generation_live_depth": {
        "file": "golden_v1_live_depth_report.json",
        "title": "Live pipeline at rerank depths 10 and 18, document prompt",
        "category": "generation",
        "label": "NEW_EVALUATION",
    },
    "citation_corrections": {
        "file": "golden_v1_phase9_citation_report.json",
        "title": "Phase 9 citation annotation corrections",
        "category": "annotation",
        "label": "OFFLINE_ANNOTATION_CORRECTION",
    },
    "ragas": {
        "file": "ragas_report.json",
        "title": "RAGAS on saved answers, configuration C",
        "category": "generation",
        "label": "NEW_EVALUATION",
    },
    "red_team": {
        "file": "redteam_report.json",
        "title": "Prompt injection red team",
        "category": "security",
        "label": "NEW_EVALUATION",
    },
}

RETRIEVAL_LABELS = {
    "vector_only": "Vector",
    "keyword_only": "Keyword",
    "rrf_1_1": "RRF 1:1",
    "rrf_2_1": "RRF 2:1",
    "rrf_3_1": "RRF 3:1",
}

LIMITATIONS = (
    "One resume corpus of 18 chunks and 39 questions.",
    "Faithfulness, relevancy, citation support and abstention come from an LLM judge.",
    "The judge is the same model as the generator.",
    "Results describe this dataset. They are not general performance guarantees.",
)


def _load(report_id):
    entry = REGISTRY.get(report_id)

    if entry is None:
        raise not_found("Evaluation")

    path = Path(config.REPORTS_DIR) / entry["file"]

    if not path.exists():
        return entry, None

    return entry, json.loads(path.read_text(encoding="utf-8"))


def _describe(report_id, entry, data):
    return {
        "id": report_id,
        "title": entry["title"],
        "category": entry["category"],
        "label": entry["label"],
        "file": entry["file"],
        "available": data is not None,
        "generated_at": data.get("generated_at") if data else None,
    }


def list_evaluations():
    return [
        _describe(report_id, *_load(report_id))
        for report_id in REGISTRY
    ]


def _mean(values):
    values = [value for value in values if value is not None]
    return round(statistics.fmean(values), 2) if values else None


def _retrieval_summary(data):
    results = data["individual_results"]
    misses = []

    for item in results:
        if item.get("answerability") != "answerable":
            continue

        metrics = item["configurations"]["rrf_3_1"]["metrics"]

        if metrics.get("recall_at_5", 1) < 1:
            misses.append({
                "question_id": item["question_id"],
                "question": item["question"],
                "relevant_chunk_ids": item["relevant_chunk_ids"],
                "retrieved_top5": item["configurations"]["rrf_3_1"]["retrieved_chunk_ids"][:5],
                "recall_at_5": metrics.get("recall_at_5"),
            })

    return {
        "dataset": data["dataset"],
        "scope": data["retrieval_configuration"]["metrics_scope"],
        "configurations": [
            {"id": key, "label": RETRIEVAL_LABELS.get(key, key), **metrics}
            for key, metrics in data["aggregate_metrics"].items()
        ],
        "latency_ms": {
            "vector_mean": _mean([r.get("latency_ms", {}).get("vector") for r in results]),
            "keyword_mean": _mean([r.get("latency_ms", {}).get("keyword") for r in results]),
        },
        "rrf_3_1_questions_below_full_recall_at_5": misses,
    }


def _reranking_summary(data):
    return {
        "dataset": data["dataset"],
        "model": data["reranker"]["model"],
        "configurations": [
            {
                "id": key,
                "label": value["label"],
                "before": value["before"],
                "after": value["after"],
                "mean_candidate_recall": value.get("mean_candidate_recall"),
            }
            for key, value in data["aggregate_metrics"].items()
        ],
        "api_usage": data["api_usage"],
    }


def _generation_summary(data):
    rows = []

    for key, value in data["primary_metrics_top3"].items():
        answerable = value["answerable"]
        unanswerable = value["unanswerable"]
        claims = answerable["claim_metrics"]
        rows.append({
            "id": key,
            "label": value["label"],
            "answerable_questions": answerable["answerable_questions"],
            "faithfulness_micro": answerable["faithfulness_micro"],
            "faithfulness_macro": answerable["faithfulness_macro"],
            "answer_relevancy_mean": answerable["answer_relevancy_mean"],
            "citation_id_validity_micro": answerable["citation_id_validity"]["micro_rate"],
            "citation_support_micro": claims["citation_support_micro"],
            "citation_support_macro": claims["citation_support_macro"],
            "citation_status_counts": claims["citation_status_counts"],
            "expected_point_coverage_micro": answerable["expected_point_coverage"]["micro_rate"],
            "unanswerable_questions": unanswerable["unanswerable_questions"],
            "correct_abstentions": unanswerable["correct_abstention_count"],
            "correct_abstention_rate": unanswerable["correct_abstention_rate"],
        })

    usage = data["api_usage"]["cumulative"]
    return {
        "dataset": data["dataset"],
        "generation_model": data["generation_configuration"]["model"],
        "judge_model": data["judge_configuration"]["v3"]["model"],
        "configurations": rows,
        "token_usage": usage["total_token_usage"],
        "total_model_latency_ms": round(usage["total_latency_ms"], 1),
        "model_calls": usage["total_executed"],
        "usage_note": usage["note"],
    }


def _citation_summary(data):
    summary = data["summary"]
    return {
        "note": (
            "Annotation corrections to how citations were scored. Answers, judge "
            "outputs and the golden dataset were not changed, so this is not a "
            "model improvement."
        ),
        "failure_instances": summary["failure_instances"],
        "corrected_instances": summary["corrected_instances"],
        "remaining_unsupported_instances": summary["remaining_unsupported_instances"],
        "patterns": [
            {
                "pattern_id": item["pattern_id"],
                "question_id": item["question_id"],
                "action": item["action"],
                "instances": item["instances"],
                "corrected_instances": item["corrected_instances"],
                "status": item["status"],
                "reason": item["reason"],
            }
            for item in data["patterns"]
        ],
        "human_review": {
            "pattern_id": "P013",
            "status": "NEEDS_HUMAN_APPROVAL",
            "instances": summary["remaining_unsupported_instances"],
            "recommendation_file": "golden_v1_p013_human_review.md",
        },
    }


def _ragas_summary(data):
    return {
        "tool": data["tool"],
        "judge_model": data["judge_model"],
        "generation_config": data["generation_config"],
        "questions": data["questions"],
        "metrics": data["summary"],
    }


def _red_team_summary(data):
    return {
        key: data[key]
        for key in (
            "model", "direct_attacks", "direct_attacks_blocked", "benign_questions",
            "benign_questions_blocked", "indirect_attacks",
            "indirect_succeeded_prompt_only", "indirect_succeeded_with_sanitizer",
        )
    } | {
        "note": (
            "Patterns were tuned on these same cases, so these are counts and not "
            "a detection rate."
        )
    }


SUMMARIES = {
    "retrieval_top18": _retrieval_summary,
    "reranking_top10": _reranking_summary,
    "reranking_deep": _reranking_summary,
    "generation": _generation_summary,
    "generation_live_depth": _generation_summary,
    "citation_corrections": _citation_summary,
    "ragas": _ragas_summary,
    "red_team": _red_team_summary,
}


def get_evaluation(report_id):
    entry, data = _load(report_id)
    result = _describe(report_id, entry, data)
    result["limitations"] = LIMITATIONS
    result["summary"] = SUMMARIES[report_id](data) if data is not None else None
    return result


def experiments_comparison():
    """One row per configuration, all from saved reports. No API is called."""

    rows = []
    entry, retrieval = _load("retrieval_top18")

    if retrieval:
        latency = _retrieval_summary(retrieval)["latency_ms"]

        for key, metrics in retrieval["aggregate_metrics"].items():
            rows.append({
                "id": f"retrieval:{key}",
                "group": "Retrieval only",
                "source_report": "retrieval_top18",
                "label": RETRIEVAL_LABELS.get(key, key),
                "candidate_pool": retrieval["retrieval_configuration"]["candidate_k"],
                "final_context_size": None,
                "precision_at_3": metrics["precision_at_3"],
                "precision_at_5": metrics["precision_at_5"],
                "precision_at_10": metrics.get("precision_at_10"),
                "recall_at_3": metrics["recall_at_3"],
                "recall_at_5": metrics["recall_at_5"],
                "recall_at_10": metrics.get("recall_at_10"),
                "mrr_at_10": metrics["mrr_at_10"],
                "latency_note": _retrieval_latency_note(key, latency),
                "status": _retrieval_status(key),
            })

    for report_id, group in (
        ("reranking_top10", "Reranked, depth 10"),
        ("reranking_deep", "Reranked, depth 10 and 18"),
    ):
        entry, data = _load(report_id)

        if not data:
            continue

        usage = data["api_usage"]
        calls = usage.get("total_logical_calls") or None
        total = usage.get("total_rerank_latency_ms") or usage.get("total_rerank_latency_ms_all_calls")

        for key, value in data["aggregate_metrics"].items():
            after = value["after"]
            rows.append({
                "id": f"{report_id}:{key}",
                "group": group,
                "source_report": report_id,
                "label": value["label"],
                "candidate_pool": value.get("depth", 10),
                "final_context_size": None,
                "precision_at_3": after["precision_at_3"],
                "precision_at_5": after["precision_at_5"],
                "precision_at_10": after.get("precision_at_10"),
                "recall_at_3": after["recall_at_3"],
                "recall_at_5": after["recall_at_5"],
                "recall_at_10": after.get("recall_at_10"),
                "mrr_at_10": after["mrr_at_10"],
                "before_mrr_at_10": value["before"]["mrr_at_10"],
                "latency_note": (
                    f"Rerank mean {round(total / calls)} ms per call" if total and calls else None
                ),
                "status": _rerank_status(key),
            })

    return {
        "rows": rows,
        "limitations": LIMITATIONS,
        "note": "Read from saved reports. Opening this view calls no external API.",
    }


def _retrieval_latency_note(key, latency):
    if key == "vector_only" and latency["vector_mean"] is not None:
        return f"Vector search mean {latency['vector_mean']} ms"

    if key == "keyword_only" and latency["keyword_mean"] is not None:
        return f"Keyword search mean {latency['keyword_mean']} ms"

    return None


def _retrieval_status(key):
    return {
        "vector_only": "comparison_baseline",
        "rrf_3_1": "experimental",
    }.get(key, "experimental")


def _rerank_status(key):
    return {
        "vector_top10": "comparison_baseline",
        "vector_top18": "comparison_baseline",
        "vector_only": "comparison_baseline",
        "rrf_3_1": "provisional_default",
    }.get(key, "experimental")
