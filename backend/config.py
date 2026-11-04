"""Environment configuration and the retrieval profiles."""

from dataclasses import asdict, dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

API_PREFIX = "/api/v1"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_DIMENSIONS = 384

UPLOAD_DIR = Path(os.getenv("RAG_UPLOAD_DIR", BASE_DIR / "uploads"))
REPORTS_DIR = Path(os.getenv("RAG_REPORTS_DIR", BASE_DIR))
MAX_UPLOAD_BYTES = int(os.getenv("RAG_MAX_UPLOAD_MB", "20")) * 1024 * 1024
MAX_PDF_PAGES = int(os.getenv("RAG_MAX_PDF_PAGES", "500"))

API_TOKEN = os.getenv("RAG_API_TOKEN", "")
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv("RAG_CORS_ORIGINS", "").split(",")
    if origin.strip()
]

CHAT_RATE_LIMIT = int(os.getenv("RAG_RATE_LIMIT_REQUESTS", "10"))
UPLOAD_RATE_LIMIT = int(os.getenv("RAG_UPLOAD_RATE_LIMIT_REQUESTS", "10"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RAG_RATE_LIMIT_WINDOW_SECONDS", "60"))

HISTORY_WINDOW_MESSAGES = 6

# Off by default, so starting the API never changes a database's schema.
AUTO_MIGRATE = os.getenv("RAG_AUTO_MIGRATE", "false").strip().lower() == "true"


@dataclass(frozen=True)
class RetrievalProfile:
    id: str
    label: str
    mode: str
    depth: int
    candidate_k: int
    vector_weight: float
    keyword_weight: float
    status: str
    evidence: str

    def as_dict(self):
        return asdict(self)


PROFILES = {
    profile.id: profile
    for profile in (
        RetrievalProfile(
            "rrf3_1_top10",
            "RRF 3:1, rerank top 10 (provisional default, experimental)",
            "rrf", 10, 18, 3.0, 1.0,
            "provisional_default",
            "Reranking benchmark at depth 10. No end-to-end generation evaluation.",
        ),
        RetrievalProfile(
            "A_vector_top10",
            "A: Vector, rerank top 10",
            "vector", 10, 10, 1.0, 0.0,
            "comparison_baseline",
            "Generation evaluation configuration A.",
        ),
        RetrievalProfile(
            "B_vector_top18",
            "B: Vector, rerank top 18",
            "vector", 18, 18, 1.0, 0.0,
            "comparison_baseline",
            "Generation evaluation configuration B.",
        ),
        RetrievalProfile(
            "C_rrf1_1_top18",
            "C: RRF 1:1, top 18",
            "rrf", 18, 18, 1.0, 1.0,
            "experimental",
            "Retrieval benchmark only. It trailed the vector baseline on MRR@10.",
        ),
        RetrievalProfile(
            "D_rrf3_1_top18",
            "D: RRF 3:1, rerank top 18",
            "rrf", 18, 18, 3.0, 1.0,
            "experimental",
            "Generation evaluation configuration C_rrf3_1_top18.",
        ),
    )
}

DEFAULT_PROFILE_ID = os.getenv("RAG_RETRIEVAL_PROFILE", "rrf3_1_top10")

if DEFAULT_PROFILE_ID not in PROFILES:
    raise ValueError(f"Unknown RAG_RETRIEVAL_PROFILE: {DEFAULT_PROFILE_ID}")

DEFAULT_SETTINGS = {
    "default_profile_id": DEFAULT_PROFILE_ID,
    "rerank_enabled": True,
    "final_context_k": 3,
    "chunk_size": 180,
    "chunk_overlap": 35,
    "grounding_check": True,
}
