"""Compare the live chat pipeline at rerank depths 10 and 18.

Only what no saved report covers is run: the platform's document prompt on the
exact contexts each depth produces. Reranks are read from the saved checkpoints
after checking that live retrieval reproduces their candidates, so no reranker
calls are made. Questions whose top-3 contexts match share one answer and one
set of judge results.

  DB_PORT=<migrated copy> python evaluate_live_pipeline_depths.py --dry-run
  DB_PORT=<migrated copy> python evaluate_live_pipeline_depths.py
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import statistics
import time

BASE_DIR = Path(__file__).resolve().parent
CHECKPOINT_PATH = BASE_DIR / "golden_v1_live_depth_checkpoint.json"
REPORT_JSON_PATH = BASE_DIR / "golden_v1_live_depth_report.json"
REPORT_MD_PATH = BASE_DIR / "golden_v1_live_depth_report.md"

DEPTHS = {
    "live_rrf3_1_top10": {
        "label": "Live pipeline: RRF 3:1, rerank top 10, document prompt",
        "profile": "rrf3_1_top10",
        "source": BASE_DIR / "golden_v1_reranking_checkpoint.json",
        "key": "rrf_3_1",
    },
    "live_rrf3_1_top18": {
        "label": "Live pipeline: RRF 3:1, rerank top 18, document prompt",
        "profile": "D_rrf3_1_top18",
        "source": BASE_DIR / "golden_v1_deep_reranking_checkpoint.json",
        "key": "rrf3_1_top18",
    },
}
TOP_K = 3


def signature(*parts):
    payload = json.dumps(parts, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_frozen_reranks():
    frozen = {}

    for name, depth in DEPTHS.items():
        calls = json.loads(depth["source"].read_text(encoding="utf-8"))["calls"]
        frozen[name] = {
            key.split("|")[0]: value
            for key, value in calls.items()
            if key.split("|")[1] == depth["key"]
        }

    return frozen


def build_plan(questions, frozen, retrieve):
    """Join each question to its frozen rerank. Stop if live retrieval differs."""

    plan = []

    for question in questions:
        question_id = question["question_id"]
        configs = {}

        for name, depth in DEPTHS.items():
            record = frozen[name][question_id]
            rows = retrieve(question["question"], depth["profile"])
            live_ids = [row["id"] for row in rows]

            if live_ids != record["before_ids"]:
                raise ValueError(
                    f"{question_id} {name}: live candidates differ from the saved rerank input."
                )

            contents = {row["id"]: row["content"] for row in rows}
            top_ids = record["after_ids"][:TOP_K]
            configs[name] = {
                "top3_ids": top_ids,
                "contexts": [{"id": i, "content": contents[i]} for i in top_ids],
                "rerank_latency_ms": record["latency_ms"],
            }

        plan.append({**question, "configs": configs})

    return plan


def count_planned_calls(plan):
    generation, judges = set(), 0

    for item in plan:
        unique = {
            signature(item["question"], config["contexts"])
            for config in item["configs"].values()
        }
        generation |= unique
        judges += len(unique) * (2 if item["answerability"] == "answerable" else 1)

    return {"generation": len(generation), "judges": judges, "total": len(generation) + judges}


def run_stage(store, key, operation, save):
    """Reuse a successful saved result, so a rerun only repeats failures."""

    saved = store.get(key)

    if saved and saved.get("status") == "OK":
        return saved

    result = operation()
    store[key] = result
    save()
    return result


def evaluate(plan, stages, checkpoint, save):
    """Fill per-question results. `stages` holds generate, v3, coverage, abstention."""

    store = checkpoint.setdefault("stages", {})
    entries = []

    for item in plan:
        for name, config in item["configs"].items():
            contexts = config["contexts"]
            base = signature(item["question"], contexts)
            generation = run_stage(
                store, f"generation:{base}",
                lambda q=item["question"], c=contexts: stages["generate"](q, c), save,
            )
            entry = {
                "question_id": item["question_id"],
                "question": item["question"],
                "config": name,
                "answerability": item["answerability"],
                "top3_ids": config["top3_ids"],
                "rerank_latency_ms": config["rerank_latency_ms"],
                "generation": generation,
                "status": "FAILED",
                "failure_stage": "generation",
            }
            entries.append(entry)

            if generation.get("status") != "OK":
                continue

            answer = generation["answer"]
            entry.update(stages["citations"](answer, contexts, config["top3_ids"]))
            failure = None

            if item["answerability"] == "answerable":
                judged = [
                    ("v3_evaluation", lambda: stages["v3"](item["question"], answer, contexts)),
                    ("expected_points", lambda: stages["coverage"](
                        item["question"], answer, item["expected_answer_points"])),
                ]
            else:
                judged = [("abstention", lambda: stages["abstention"](
                    item["question"], answer, contexts,
                    item["why_unanswerable"], item["expected_behavior"]))]

            for stage, operation in judged:
                result = run_stage(store, f"{stage}:{base}", operation, save)
                entry[stage] = result

                if result.get("status") != "OK" and failure is None:
                    failure = stage

            entry["status"] = "OK" if failure is None else "FAILED"
            entry["failure_stage"] = failure

    return entries


def retrieval_metrics(plan, name):
    recalls, precisions, reciprocal = [], [], []

    for item in plan:
        relevant = set(item.get("relevant_chunk_ids") or [])

        if item["answerability"] != "answerable":
            continue

        top = item["configs"][name]["top3_ids"]
        hits = [chunk for chunk in top if chunk in relevant]
        recalls.append(len(hits) / len(relevant))
        precisions.append(len(hits) / len(top))
        reciprocal.append(
            next((1 / (i + 1) for i, chunk in enumerate(top) if chunk in relevant), 0.0)
        )

    return {
        "precision_at_3": statistics.mean(precisions),
        "recall_at_3": statistics.mean(recalls),
        "mrr_at_3": statistics.mean(reciprocal),
    }


def percentile(values, share):
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(share * len(ordered)))] if ordered else None


def cost_and_latency(entries, name):
    selected = [entry for entry in entries if entry["config"] == name]
    tokens = {"generation": 0, "judges": 0}
    generation_ms = []

    for entry in selected:
        generation_ms.append(entry["generation"].get("latency_ms") or 0)
        tokens["generation"] += (entry["generation"].get("usage") or {}).get("total_tokens") or 0

        for stage in ("v3_evaluation", "expected_points", "abstention"):
            tokens["judges"] += ((entry.get(stage) or {}).get("usage") or {}).get("total_tokens") or 0

    rerank_ms = [entry["rerank_latency_ms"] for entry in selected]
    return {
        "generation_tokens_if_run_alone": tokens["generation"],
        "judge_tokens_if_run_alone": tokens["judges"],
        "generation_latency_ms_p50": percentile(generation_ms, 0.5),
        "generation_latency_ms_p95": percentile(generation_ms, 0.95),
        "saved_rerank_latency_ms_p50": percentile(rerank_ms, 0.5),
        "saved_rerank_latency_ms_p95": percentile(rerank_ms, 0.95),
    }


def build_report(plan, entries, checkpoint, generation_model, judge_model, dataset_meta):
    import evaluate_golden_v1_generation as ev

    primary, retrieval_rows, costs = {}, {}, {}

    for name, depth in DEPTHS.items():
        ev.CONFIGS[name] = {"label": depth["label"]}
        primary[name] = {
            "label": depth["label"],
            "answerable": ev.aggregate_answerable(entries, name),
            "unanswerable": ev.aggregate_unanswerable(entries, name),
        }
        retrieval_rows[name] = retrieval_metrics(plan, name)
        costs[name] = cost_and_latency(entries, name)

    stages = checkpoint.get("stages", {}).values()
    latency = sum(stage.get("latency_ms") or 0 for stage in stages)
    usage_totals = {
        key: sum((stage.get("usage") or {}).get(key) or 0 for stage in stages)
        for key in ("prompt_tokens", "completion_tokens", "total_tokens")
    }
    first, second = list(DEPTHS)
    differing = [
        item["question_id"] for item in plan
        if item["configs"][first]["top3_ids"] != item["configs"][second]["top3_ids"]
    ]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "phase": "Live pipeline depth comparison",
        "label": "NEW_EVALUATION",
        "dataset": dataset_meta,
        "generation_configuration": {"model": generation_model, "prompt": "DOCUMENT_SYSTEM_PROMPT"},
        "judge_configuration": {"v3": {"model": judge_model}},
        "primary_metrics_top3": primary,
        "retrieval_top3": retrieval_rows,
        "cost_and_latency": costs,
        "questions_with_different_top3": differing,
        "api_usage": {"cumulative": {
            "total_token_usage": usage_totals,
            "total_latency_ms": latency,
            "total_executed": len(checkpoint.get("stages", {})),
            "note": (
                "Calls actually made. Questions with identical contexts shared one answer "
                "and judge result. Reranks reused from saved checkpoints. The runtime "
                "grounding check is not included."
            ),
        }},
        "notes": [
            "Reranks are reused, so rerank latency comes from the earlier saved runs.",
            "The judge is the same model as the generator.",
            "This resume dataset cannot pick a winner. A second dataset is still required.",
        ],
        "per_question_results": entries,
    }


def render_markdown(report):
    lines = [
        "# Live pipeline: rerank depth 10 and 18", "",
        "Label: NEW_EVALUATION. Same document prompt and live retrieval for both. "
        "The judge is the same model as the generator. One resume dataset, so this does not pick a winner.",
        "",
        "| Measure | Depth 10 | Depth 18 |", "|---|---:|---:|",
    ]
    a, b = (report["primary_metrics_top3"][name] for name in DEPTHS)
    ra, rb = (report["retrieval_top3"][name] for name in DEPTHS)
    ca, cb = (report["cost_and_latency"][name] for name in DEPTHS)

    def row(title, left, right):
        lines.append(f"| {title} | {left} | {right} |")

    def fmt(value):
        return "n/a" if value is None else f"{value:.4f}"

    for key, title in (("recall_at_3", "Recall@3"), ("precision_at_3", "Precision@3")):
        row(title, fmt(ra[key]), fmt(rb[key]))

    for title, read in (
        ("Faithfulness, micro", lambda s: s["answerable"]["faithfulness_micro"]),
        ("Answer relevancy, 1 to 5", lambda s: s["answerable"]["answer_relevancy_mean"]),
        ("Citation-ID validity", lambda s: s["answerable"]["citation_id_validity"]["micro_rate"]),
        ("Citation support, micro", lambda s: s["answerable"]["claim_metrics"]["citation_support_micro"]),
        ("Citation support, macro", lambda s: s["answerable"]["claim_metrics"]["citation_support_macro"]),
        ("Expected-point coverage, micro", lambda s: s["answerable"]["expected_point_coverage"]["micro_rate"]),
    ):
        row(title, fmt(read(a)), fmt(read(b)))

    row("Correct abstention",
        f"{a['unanswerable']['correct_abstention_count']}/{a['unanswerable']['unanswerable_questions']}",
        f"{b['unanswerable']['correct_abstention_count']}/{b['unanswerable']['unanswerable_questions']}")
    row("Generation tokens, 39 questions", ca["generation_tokens_if_run_alone"], cb["generation_tokens_if_run_alone"])
    row("Generation latency p50, ms", round(ca["generation_latency_ms_p50"]), round(cb["generation_latency_ms_p50"]))
    row("Generation latency p95, ms", round(ca["generation_latency_ms_p95"]), round(cb["generation_latency_ms_p95"]))
    row("Saved rerank latency p50, ms", round(ca["saved_rerank_latency_ms_p50"]), round(cb["saved_rerank_latency_ms_p50"]))
    row("Saved rerank latency p95, ms", round(ca["saved_rerank_latency_ms_p95"]), round(cb["saved_rerank_latency_ms_p95"]))
    usage = report["api_usage"]["cumulative"]
    lines += [
        "",
        f"Top-3 contexts differ on {len(report['questions_with_different_top3'])} of 39 questions: "
        + ", ".join(report["questions_with_different_top3"]) + ".",
        f"Model calls made: {usage['total_executed']}. Tokens: {usage['total_token_usage']['total_tokens']}. {usage['note']}",
        "",
    ]
    return "\n".join(lines)


def live_stages():
    import evaluate_golden_v1_generation as ev
    from backend.chat_service import DOCUMENT_SYSTEM_PROMPT
    from guardrails import sanitize_chunks
    import rag_chat as engine

    def generate(question, contexts):
        captured = {}
        engine.record_usage = lambda response: captured.update(usage=ev._extract_usage(response))
        safe_rows, _flagged = sanitize_chunks(contexts)
        started = time.perf_counter()

        for attempt in range(2):
            try:
                answer = engine.generate_answer(
                    question, safe_rows, None, system_prompt=DOCUMENT_SYSTEM_PROMPT
                )
                return {
                    "status": "OK",
                    "answer": answer,
                    "attempts": attempt + 1,
                    "latency_ms": (time.perf_counter() - started) * 1000,
                    "usage": captured.get("usage"),
                }
            except Exception as error:
                failure = type(error).__name__
                time.sleep(2)

        return {"status": "ERROR", "error_type": failure, "attempts": 2,
                "latency_ms": (time.perf_counter() - started) * 1000}

    def citations(answer, contexts, top_ids):
        validation = ev.validate_citations(answer, contexts)
        return {
            "citation_validation": validation,
            "citation_id_validity": ev.citation_id_metrics(validation, answer, top_ids),
        }

    return {
        "generate": generate,
        "citations": citations,
        "v3": ev.run_v3_stage,
        "coverage": ev.run_coverage_stage,
        "abstention": ev.run_abstention_stage,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Count calls. No model is called.")
    args = parser.parse_args()

    if os.getenv("DB_PORT", "5433") == "5433":
        raise SystemExit("Set DB_PORT to a migrated copy. This reads the platform tables.")

    import evaluate_golden_v1_generation as ev
    from backend import config, retrieval
    from backend.db import connection
    import rag_chat as engine

    dataset = ev.load_dataset()
    frozen = load_frozen_reranks()
    model = engine.get_embedding_model()

    def retrieve(question, profile_id):
        with connection() as conn:
            rows, mode = retrieval.retrieve(conn, question, model, config.PROFILES[profile_id])

        if mode != "hybrid":
            raise ValueError(f"Expected hybrid retrieval, got {mode}.")

        return rows

    plan = build_plan(dataset["questions"], frozen, retrieve)
    print("Live retrieval reproduces the saved rerank inputs for every question and depth.")
    print("Planned calls:", count_planned_calls(plan))

    if args.dry_run:
        return

    checkpoint = (
        json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))
        if CHECKPOINT_PATH.exists() else {}
    )

    def save():
        temporary = CHECKPOINT_PATH.with_suffix(".tmp")
        temporary.write_text(json.dumps(checkpoint, ensure_ascii=False), encoding="utf-8")
        temporary.replace(CHECKPOINT_PATH)

    entries = evaluate(plan, live_stages(), checkpoint, save)
    report = build_report(
        plan, entries, checkpoint, engine.NVIDIA_MODEL, ev.V3_JUDGE_SETTINGS["model"],
        json.loads((BASE_DIR / "golden_v1_generation_report.json").read_text(encoding="utf-8"))["dataset"],
    )
    REPORT_JSON_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    REPORT_MD_PATH.write_text(render_markdown(report), encoding="utf-8")
    failed = [entry for entry in entries if entry["status"] != "OK"]
    print(f"Done. {len(entries) - len(failed)} of {len(entries)} entries OK.")
    print(render_markdown(report))


if __name__ == "__main__":
    main()
