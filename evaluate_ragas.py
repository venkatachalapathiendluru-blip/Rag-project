"""Score saved golden-dataset answers with RAGAS metrics.

Run with the separate environment: .venv-ragas/bin/python evaluate_ragas.py
Options: --limit N (first N questions), --config NAME (saved configuration).
Answers are not regenerated: this scores the saved generation checkpoint.
"""

import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import statistics

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
import psycopg
from ragas import EvaluationDataset, evaluate
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import (
    Faithfulness,
    LLMContextPrecisionWithReference,
    LLMContextRecall,
)
from ragas.run_config import RunConfig


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
REPORT = BASE_DIR / "ragas_report.json"


def load_chunks():
    with psycopg.connect(
        dbname="rag_db",
        user="rag_user",
        password=os.environ["DB_PASSWORD"],
        host="localhost",
        port=5433,
    ) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT id, content FROM public.documents")
        return dict(cursor.fetchall())


def build_samples(config, limit=None):
    checkpoint = json.loads(
        (BASE_DIR / "golden_v1_generation_checkpoint.json").read_text(encoding="utf-8")
    )
    dataset = json.loads(
        (BASE_DIR / "golden_dataset_v1_reviewed.json").read_text(encoding="utf-8")
    )
    questions = {item["question_id"]: item for item in dataset["questions"]}
    chunks = load_chunks()
    samples = []

    for call in checkpoint["calls"].values():
        if call["config"] != config or call["answerability"] != "answerable":
            continue

        question = questions[call["question_id"]]
        samples.append({
            "question_id": call["question_id"],
            "user_input": question["question"],
            "response": call["generation"]["answer"],
            "retrieved_contexts": [chunks[i] for i in call["top3_ids"] if i in chunks],
            "reference": " ".join(question["expected_answer_points"]),
        })

    samples.sort(key=lambda sample: sample["question_id"])
    return samples[:limit] if limit else samples


def clean_mean(values):
    valid = [v for v in values if isinstance(v, (int, float)) and not math.isnan(v)]
    return (round(statistics.mean(valid), 4) if valid else None), len(valid)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int)
    parser.add_argument("--config", default="C_rrf3_1_top18")
    args = parser.parse_args()

    samples = build_samples(args.config, args.limit)
    judge = LangchainLLMWrapper(
        ChatOpenAI(
            model=os.environ["NVIDIA_MODEL"],
            base_url=os.environ["NVIDIA_BASE_URL"],
            api_key=os.environ["NVIDIA_API_KEY"],
            temperature=0,
            max_tokens=4096,
        )
    )
    metrics = [Faithfulness(), LLMContextRecall(), LLMContextPrecisionWithReference()]
    dataset = EvaluationDataset.from_list([
        {key: value for key, value in sample.items() if key != "question_id"}
        for sample in samples
    ])
    result = evaluate(
        dataset,
        metrics=metrics,
        llm=judge,
        run_config=RunConfig(max_workers=2, timeout=240, max_retries=4),
        raise_exceptions=False,
        show_progress=False,
    )
    rows = result.to_pandas().to_dict(orient="records")
    names = [metric.name for metric in metrics]
    summary = {}

    for name in names:
        mean, scored = clean_mean([row.get(name) for row in rows])
        summary[name] = {"mean": mean, "scored": scored, "of": len(rows)}

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tool": "ragas",
        "judge_model": os.environ["NVIDIA_MODEL"],
        "generation_config": args.config,
        "questions": len(samples),
        "summary": summary,
        "per_question": [
            {
                "question_id": sample["question_id"],
                **{name: row.get(name) for name in names},
            }
            for sample, row in zip(samples, rows)
        ],
    }
    output = REPORT if not args.limit else BASE_DIR / "ragas_report_sample.json"
    output.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
