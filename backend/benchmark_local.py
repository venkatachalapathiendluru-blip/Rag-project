"""Local performance benchmark. It makes no external API calls.

Usage: DB_PORT=<disposable> python -m backend.benchmark_local [chunk_count]
It adds a temporary document and removes it again. It refuses port 5433.
"""

from concurrent.futures import ThreadPoolExecutor
import json
import os
import resource
import statistics
import sys
import time

from backend import config, retrieval
from backend.db import close_pool, connection
from rag_chat import get_embedding_model


QUESTIONS = [
    "What backend frameworks are mentioned?",
    "How often are safety reports filed?",
    "Which database stores the vectors?",
    "Describe the reranking step",
    "Who leads the project?",
]


def timed(function, repeat):
    samples = []

    for index in range(repeat):
        started = time.perf_counter()
        function(index)
        samples.append((time.perf_counter() - started) * 1000)

    samples.sort()
    return {
        "p50_ms": round(statistics.median(samples), 1),
        "p95_ms": round(samples[int(len(samples) * 0.95) - 1], 1),
    }


def main(count=5000):
    if os.getenv("DB_PORT", "5433") == "5433":
        raise SystemExit("Refusing the real database. Set DB_PORT to a disposable one.")

    model = get_embedding_model()
    texts = [
        f"Synthetic record {index} about topic {index % 97} with detail {index * 7 % 1009}."
        for index in range(count)
    ]
    started = time.perf_counter()
    embeddings = model.encode(texts, batch_size=32, normalize_embeddings=True, convert_to_numpy=True)
    embed_seconds = time.perf_counter() - started

    with connection() as conn:
        document_id = conn.execute(
            """
            INSERT INTO source_documents (filename, media_type, version, status, chunk_count)
            VALUES ('benchmark-temporary.txt', 'text/plain', 1, 'ready', %s) RETURNING id
            """,
            (count,),
        ).fetchone()[0]
        started = time.perf_counter()

        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO document_chunks (source_document_id, document_version, chunk_index, content, embedding)
                VALUES (%s, 1, %s, %s, %s::vector)
                """,
                [
                    (document_id, index, text, retrieval.to_vector_literal(vector))
                    for index, (text, vector) in enumerate(zip(texts, embeddings))
                ],
            )

        insert_seconds = time.perf_counter() - started

    results = {
        "chunks": count,
        "embedding_chunks_per_second": round(count / embed_seconds, 1),
        "insert_chunks_per_second": round(count / insert_seconds, 1),
        "retrieval": {},
    }

    try:
        for profile_id in ("A_vector_top10", "D_rrf3_1_top18"):
            profile = config.PROFILES[profile_id]

            def run(index, profile=profile):
                with connection() as conn:
                    retrieval.retrieve(conn, QUESTIONS[index % len(QUESTIONS)], model, profile)

            results["retrieval"][profile_id] = timed(run, 40)

        profile = config.PROFILES["D_rrf3_1_top18"]

        def one(index):
            with connection() as conn:
                retrieval.retrieve(conn, QUESTIONS[index % len(QUESTIONS)], model, profile)

        started = time.perf_counter()

        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(one, range(40)))

        results["concurrent_8_workers_requests_per_second"] = round(40 / (time.perf_counter() - started), 1)
    finally:
        with connection() as conn:
            conn.execute("DELETE FROM source_documents WHERE id = %s", (document_id,))

    results["peak_rss_mb"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024)
    close_pool()
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main(*map(int, sys.argv[1:2]))
