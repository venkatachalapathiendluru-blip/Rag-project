"""Request and response models."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from guardrails import MAX_QUESTION_CHARS


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=MAX_QUESTION_CHARS)
    conversation_id: Optional[int] = Field(default=None, gt=0)
    profile_id: Optional[str] = None
    document_ids: Optional[list[int]] = Field(default=None, max_length=100)


class Citation(BaseModel):
    chunk_id: int
    document_id: int
    filename: str
    page_number: Optional[int]
    chunk_index: int
    document_version: int
    content: str
    similarity: float
    rerank_score: Optional[float]


class Validation(BaseModel):
    citation_ids_valid: Optional[bool]
    cited_ids: list[str]
    invalid_ids: list[str]
    grounding_status: str
    grounded: Optional[bool]
    unsupported_claims: list[str]
    rerank_status: Optional[str]
    retrieval_mode: Optional[str]
    flagged_chunk_ids: list[Any]
    input_guardrail_reasons: list[str]
    output_guardrail_reasons: list[str]


class ChatResponse(BaseModel):
    conversation_id: int
    message_id: int
    answer: str
    status: str
    citations: list[Citation]
    validation: Validation
    profile_id: str
    trace_id: str
    retrieval_question: str
    latency_ms: float


class Message(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime
    status: Optional[str]
    citations: Optional[list[Citation]]
    validation: Optional[Validation]
    profile_id: Optional[str]
    trace_id: Optional[str]


class ConversationSummary(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int


class Conversation(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[Message]


class Document(BaseModel):
    id: int
    filename: str
    media_type: str
    size_bytes: Optional[int]
    page_count: Optional[int]
    version: int
    status: str
    error: Optional[str]
    chunk_size: Optional[int]
    chunk_overlap: Optional[int]
    chunk_count: int
    is_protected: bool
    created_at: datetime
    updated_at: datetime
    indexed_at: Optional[datetime]


class Job(BaseModel):
    id: int
    source_document_id: int
    kind: str
    status: str
    filename: str
    size_bytes: int
    chunk_size: int
    chunk_overlap: int
    chunks_created: Optional[int]
    error: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]


class Chunk(BaseModel):
    id: int
    chunk_index: int
    page_number: Optional[int]
    content: str
    document_version: int


class DocumentDetail(Document):
    jobs: list[Job]
    chunks: list[Chunk]


class UploadAccepted(BaseModel):
    document_id: int
    job_id: int


class SettingsModel(BaseModel):
    default_profile_id: str
    rerank_enabled: bool
    final_context_k: int
    chunk_size: int
    chunk_overlap: int
    grounding_check: bool


class SettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_profile_id: Optional[str] = None
    rerank_enabled: Optional[bool] = None
    final_context_k: Optional[int] = None
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
    grounding_check: Optional[bool] = None
