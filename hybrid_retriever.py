import re


# Generalized domain-based query expansion.

QUERY_EXPANSION_RULES = {
    "backend": {
        "patterns": [
            r"\bbackend\b",
            r"\bpython\b",
            r"\bdjango\b",
            r"\bfastapi\b",
            r"\bdrf\b",
            r"\bapi development\b",
            r"\bapi\b",
            r"\bmicroservices?\b",
            r"\bserver[- ]side\b",
        ],
        "terms": [
            "python", "django", "drf", "fastapi",
            "backend", "rest", "api", "microservices",
            "asynchronous", "validation", "pagination",
            "filtering",
        ],
    },

    "genai": {
        "patterns": [
            r"\bgen.?ai\b",
            r"\bgenerative ai\b",
            r"\bllm\b",
            r"\bopenai\b",
            r"\banthropic\b",
            r"\bclaude\b",
            r"\bprompt engineering\b",
            r"\bartificial intelligence\b",
        ],
        "terms": [
            "generative", "ai", "llm", "openai",
            "anthropic", "claude", "prompt",
            "langchain", "langgraph", "embeddings",
            "rag", "automation",
        ],
    },

    "rag": {
        "patterns": [
            r"\brag\b",
            r"\bretrieval augmented\b",
            r"\bdocument question answering\b",
            r"\bdocument retrieval\b",
            r"\bretrieval architecture\b",
            r"\bvector search\b",
            r"\bsemantic search\b",
            r"\bcontext grounded\b",
        ],
        "terms": [
            "rag", "retrieval", "augmented",
            "generation", "document", "question",
            "answering", "chunking", "embeddings",
            "vector", "semantic", "search",
        ],
    },

    "aws": {
        "patterns": [
            r"\baws\b",
            r"\bamazon web services\b",
            r"\bcloud services\b",
            r"\bcloud infrastructure\b",
        ],
        "terms": [
            "aws", "ec2", "s3", "rds", "ses",
            "lambda", "cloudwatch", "iam",
        ],
    },

    "databases": {
        "patterns": [
            r"\bdatabase\b",
            r"\bdatabases\b",
            r"\bpostgresql\b",
            r"\bmysql\b",
            r"\bredis\b",
            r"\bcaching\b",
            r"\bbackground jobs?\b",
            r"\bscheduled jobs?\b",
        ],
        "terms": [
            "postgresql", "mysql", "redis",
            "celery", "database", "caching",
            "background", "scheduled", "jobs",
        ],
    },

    "orchestration": {
        "patterns": [
            r"\blangchain\b",
            r"\blanggraph\b",
            r"\btool calling\b",
            r"\bfunction calling\b",
            r"\bagent workflows?\b",
            r"\bllm orchestration\b",
        ],
        "terms": [
            "langchain", "langgraph", "tool",
            "calling", "function", "workflows",
            "orchestration", "multi", "step",
        ],
    },

    "security": {
        "patterns": [
            r"\bauthentication\b",
            r"\bauthorization\b",
            r"\bsecurity\b",
            r"\boauth\b",
            r"\bjwt\b",
            r"\brbac\b",
            r"\bsso\b",
            r"\baccess control\b",
        ],
        "terms": [
            "authentication", "authorization",
            "oauth", "jwt", "rbac", "sso",
            "permissions", "security", "access",
            "control",
        ],
    },

    "integrations": {
        "patterns": [
            r"\bintegrations?\b",
            r"\bexternal services?\b",
            r"\bthird[- ]party\b",
            r"\bwebhooks?\b",
            r"\bjira\b",
            r"\bzendesk\b",
            r"\bzoho\b",
                r"\bexternal platforms?\b",
                r"\bplatforms? have i connected\b",
                r"\bconnected platforms?\b",
        ],
        "terms": [
            "jira", "zendesk", "zoho",
            "sheets", "calendar", "exotel",
            "webhooks", "integrations",
            "external", "services", "rest", "apis",
        ],
    },

    "education": {
        "patterns": [
            r"\beducation\b",
            r"\bqualifications?\b",
            r"\bdegree\b",
            r"\buniversity\b",
            r"\bacademic\b",
        ],
        "terms": [
            "bachelor", "science", "computer",
            "education", "university", "degree",
        ],
    },
}


METRIC_NAMES = [
    "precision_at_3",
    "recall_at_3",
    "precision_at_5",
    "recall_at_5",
    "precision_at_10",
    "recall_at_10",
    "mrr_at_10",
]


def get_expansion_terms(question):
    """
    Detect relevant technical domains from any question wording.
    Multiple domains can be activated.
    """

    question_lower = question.lower()

    matched_terms = []

    for domain, rule in QUERY_EXPANSION_RULES.items():

        matched = any(
            re.search(pattern, question_lower)
            for pattern in rule["patterns"]
        )

        if matched:
            matched_terms.extend(rule["terms"])

    # Fallback for questions that match no known domain.
    if not matched_terms:
        matched_terms = re.findall(
            r"[a-zA-Z0-9_]+",
            question_lower
        )

    # Remove duplicates.
    return list(dict.fromkeys(matched_terms))


def build_keyword_query(question):
    """
    Build PostgreSQL OR-based full-text search query.
    """

    terms = get_expansion_terms(question)

    return " | ".join(terms)


def retrieve_hybrid_context(
    question,
    embedding_model,
    get_db_connection,
    top_k=10,
    candidate_k=18,
    vector_weight=1.0,
    keyword_weight=1.0,
):
    """
    Hybrid retrieval using:
    1. Vector search
    2. Expanded PostgreSQL full-text search
    3. Reciprocal Rank Fusion
    """

    if not question or not question.strip():
        return []

    query_embedding = embedding_model.encode(
        question,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    vector_literal = (
        "[" + ",".join(map(str, query_embedding.tolist())) + "]"
    )

    keyword_query = build_keyword_query(question)

    conn = get_db_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                WITH vector_candidates AS (

                    SELECT
                        id,
                        content,
                        1 - (embedding <=> %s::vector)
                            AS similarity,

                        ROW_NUMBER() OVER (
                            ORDER BY embedding <=> %s::vector
                        ) AS vector_rank

                    FROM documents
                    WHERE embedding IS NOT NULL

                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                ),

                keyword_query AS (

                    SELECT to_tsquery(
                        'english',
                        %s
                    ) AS query

                ),

                keyword_candidates AS (

                    SELECT
                        d.id,
                        d.content,

                        ts_rank_cd(
                            to_tsvector('english', d.content),
                            q.query
                        ) AS keyword_score,

                        ROW_NUMBER() OVER (
                            ORDER BY
                                ts_rank_cd(
                                    to_tsvector('english', d.content),
                                    q.query
                                ) DESC,
                                d.id
                        ) AS keyword_rank

                    FROM documents d
                    CROSS JOIN keyword_query q

                    WHERE to_tsvector(
                        'english',
                        d.content
                    ) @@ q.query

                    ORDER BY keyword_score DESC, d.id
                    LIMIT %s
                ),

                combined AS (

                    SELECT
                        COALESCE(v.id, k.id) AS id,

                        COALESCE(
                            v.content,
                            k.content
                        ) AS content,

                        COALESCE(
                            v.similarity,
                            0.0
                        ) AS similarity,

                        COALESCE(
                            %s::float / (60 + v.vector_rank),
                            0.0
                        )
                        +
                        COALESCE(
                            %s::float / (60 + k.keyword_rank),
                            0.0
                        ) AS rrf_score

                    FROM vector_candidates v

                    FULL OUTER JOIN keyword_candidates k
                        ON v.id = k.id
                )

                SELECT id, content, similarity
                FROM combined
                ORDER BY rrf_score DESC, id
                LIMIT %s;
                """,
                (
                    vector_literal,
                    vector_literal,
                    vector_literal,
                    candidate_k,
                    keyword_query,
                    candidate_k,
                    vector_weight,
                    keyword_weight,
                    top_k,
                ),
            )

            return cur.fetchall()

    finally:
        conn.close()

