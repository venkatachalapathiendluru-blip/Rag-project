import os
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=True)

API_KEY = os.getenv("NVIDIA_API_KEY")
RERANK_URL = os.getenv("NVIDIA_RERANK_URL")
RERANK_MODEL = os.getenv("NVIDIA_RERANK_MODEL")


def rerank_documents(query, passages):

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    payload = {
        "model": RERANK_MODEL,
        "query": {
            "text": query
        },
        "passages": [
            {"text": passage}
            for passage in passages
        ],
        "truncate": "END"
    }

    response = requests.post(
        RERANK_URL,
        headers=headers,
        json=payload,
        timeout=120
    )

    if not response.ok:
        raise RuntimeError(
            f"NVIDIA API Error {response.status_code}: "
            f"{response.text}"
        )

    return response.json()


if __name__ == "__main__":

    query = "What Python backend technologies do I know?"

    passages = [
        "I have experience with Python, Django, Django REST Framework and FastAPI.",
        "I have worked with AWS EC2, S3, Lambda and CloudWatch.",
        "I have experience with PostgreSQL, MySQL, Redis and Celery."
    ]

    result = rerank_documents(query, passages)

    print("\nNVIDIA RERANKER SUCCESS")

    for item in result["rankings"]:
        index = item["index"]
        score = item["logit"]

        print(f"\nRanked document: {index + 1}")
        print(f"Relevance score: {score}")
        print(f"Content: {passages[index]}")
