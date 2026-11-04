"""Check platform retrieval against the saved benchmark, with no external API calls.

Usage: python -m backend.replay_golden_retrieval [output.json]
It writes a new file and leaves the saved reports unchanged.
"""

from datetime import datetime, timezone
import json
import sys

from backend import config, retrieval
from backend.config import RetrievalProfile
from backend.db import BASELINE_FILENAME, close_pool, connection
from rag_chat import get_embedding_model


CONFIGS = {
    "vector_only": RetrievalProfile("vector", "", "vector", 18, 18, 1, 0, "", ""),
    "rrf_1_1": RetrievalProfile("rrf1", "", "rrf", 18, 18, 1, 1, "", ""),
    "rrf_3_1": RetrievalProfile("rrf3", "", "rrf", 18, 18, 3, 1, "", ""),
}


def main(output="platform_retrieval_replay.json"):
    benchmark = json.loads(
        (config.REPORTS_DIR / "golden_v1_rrf_top18_benchmark.json").read_text(encoding="utf-8")
    )
    model = get_embedding_model()
    mismatches = []
    compared = 0

    with connection() as conn:
        baseline = conn.execute(
            "SELECT id FROM source_documents WHERE filename = %s", (BASELINE_FILENAME,)
        ).fetchone()[0]

        for item in benchmark["individual_results"]:
            for name, profile in CONFIGS.items():
                expected = item["configurations"][name]["retrieved_chunk_ids"]
                rows, _mode = retrieval.retrieve(conn, item["question"], model, profile, [baseline])
                actual = [row["id"] for row in rows][: len(expected)]
                compared += 1

                if actual != expected:
                    mismatches.append({
                        "question_id": item["question_id"], "config": name,
                        "expected": expected, "actual": actual,
                    })

    close_pool()
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "benchmark": "golden_v1_rrf_top18_benchmark.json",
        "comparisons": compared,
        "exact_rank_matches": compared - len(mismatches),
        "mismatches": mismatches,
    }

    with open(output, "w", encoding="utf-8") as file:
        json.dump(result, file, indent=2)

    print(f"{result['exact_rank_matches']}/{compared} rank lists match the benchmark")
    return 0 if not mismatches else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:2]))
