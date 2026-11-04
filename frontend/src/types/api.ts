export interface Citation {
  chunk_id: number
  document_id: number
  filename: string
  page_number: number | null
  chunk_index: number
  document_version: number
  content: string
  similarity: number
  rerank_score: number | null
}

export interface Validation {
  citation_ids_valid: boolean | null
  cited_ids: string[]
  invalid_ids: string[]
  grounding_status: string
  grounded: boolean | null
  unsupported_claims: string[]
  rerank_status: string | null
  retrieval_mode: string | null
  flagged_chunk_ids: number[]
  input_guardrail_reasons: string[]
  output_guardrail_reasons: string[]
}

export type AnswerStatus = 'answered' | 'no_evidence_cited' | 'no_documents' | 'blocked'

export interface ChatResponse {
  conversation_id: number
  message_id: number
  answer: string
  status: AnswerStatus
  citations: Citation[]
  validation: Validation
  profile_id: string
  trace_id: string
  retrieval_question: string
  latency_ms: number
}

export interface Message {
  id: number
  role: 'user' | 'assistant'
  content: string
  created_at: string
  status: AnswerStatus | null
  citations: Citation[] | null
  validation: Validation | null
  profile_id: string | null
  trace_id: string | null
}

export interface ConversationSummary {
  id: number
  title: string
  created_at: string
  updated_at: string
  message_count: number
}

export interface Conversation extends Omit<ConversationSummary, 'message_count'> {
  messages: Message[]
}

export interface DocumentItem {
  id: number
  filename: string
  media_type: string
  size_bytes: number | null
  page_count: number | null
  version: number
  status: 'processing' | 'ready' | 'failed'
  error: string | null
  chunk_size: number | null
  chunk_overlap: number | null
  chunk_count: number
  is_protected: boolean
  created_at: string
  updated_at: string
  indexed_at: string | null
}

export interface Job {
  id: number
  source_document_id: number
  kind: 'upload' | 'replace' | 'reindex'
  status: 'queued' | 'running' | 'succeeded' | 'failed'
  filename: string
  size_bytes: number
  chunk_size: number
  chunk_overlap: number
  chunks_created: number | null
  error: string | null
  created_at: string
  started_at: string | null
  finished_at: string | null
}

export interface Chunk {
  id: number
  chunk_index: number
  page_number: number | null
  content: string
  document_version: number
}

export interface DocumentDetail extends DocumentItem {
  jobs: Job[]
  chunks: Chunk[]
}

export interface Profile {
  id: string
  label: string
  mode: string
  depth: number
  candidate_k: number
  vector_weight: number
  keyword_weight: number
  status: string
  evidence: string
}

export interface Settings {
  default_profile_id: string
  rerank_enabled: boolean
  final_context_k: number
  chunk_size: number
  chunk_overlap: number
  grounding_check: boolean
}

export interface AppConfig {
  embedding_model: string
  embedding_dimensions: number
  generation_model: string | null
  reranker_model: string | null
  profiles: Profile[]
  settings: Settings
  limits: {
    max_upload_mb: number
    max_pdf_pages: number
    supported_types: string[]
    history_window_messages: number
    settings_ranges: Record<string, [number, number]>
  }
  security: { api_token_required: boolean; provider_configured: boolean }
  streaming_supported: boolean
}

export interface Overview {
  counts: { documents: number; chunks: number; conversations: number; queries: number }
  recent_queries: { conversation_id: number; question: string; created_at: string }[]
  recent_jobs: Job[]
  models: Pick<AppConfig, 'embedding_model' | 'embedding_dimensions' | 'generation_model' | 'reranker_model'>
  health: { api: boolean; database: { ok: boolean; detail: string }; provider_configured: boolean }
}

export interface Metrics {
  requests: number
  statuses: Record<string, number>
  guardrail_events: Record<string, number>
  citation_failures: number
  chunks_with_injection_removed: number
  total_tokens: number
  latency_ms: Record<string, { p50: number | null; p95: number | null }>
  recent_errors: { trace_id: string; started_at: string; error_type: string | null }[]
  recent_requests: { trace_id: string; started_at: string; status: string; duration_ms: number | null; total_tokens: number | null }[]
  ingestion_jobs: Job[]
  not_collected: string[]
}

export type EvaluationLabel = 'ORIGINAL_EVALUATION' | 'OFFLINE_ANNOTATION_CORRECTION' | 'NEW_EVALUATION' | 'HUMAN_APPROVED_ANNOTATION'

export interface EvaluationItem {
  id: string
  title: string
  category: string
  label: EvaluationLabel
  file: string
  available: boolean
  generated_at: string | null
}

export interface Evaluation<S = unknown> extends EvaluationItem {
  limitations: string[]
  summary: S | null
}

export interface RetrievalMetrics {
  id: string
  label: string
  precision_at_3: number
  recall_at_3: number
  precision_at_5: number
  recall_at_5: number
  precision_at_10: number
  recall_at_10: number
  mrr_at_10: number
}

export interface DatasetInfo {
  question_count: number
  answerable_count: number
  unanswerable_count: number
  review_status: string
}

export interface RetrievalSummary {
  dataset: DatasetInfo
  scope: string
  configurations: RetrievalMetrics[]
  latency_ms: { vector_mean: number | null; keyword_mean: number | null }
  rrf_3_1_questions_below_full_recall_at_5: {
    question_id: string
    question: string
    relevant_chunk_ids: number[]
    retrieved_top5: number[]
    recall_at_5: number
  }[]
}

export interface GenerationRow {
  id: string
  label: string
  answerable_questions: number
  faithfulness_micro: number
  faithfulness_macro: number
  answer_relevancy_mean: number
  citation_id_validity_micro: number
  citation_support_micro: number
  citation_support_macro: number
  citation_status_counts: Record<string, number>
  expected_point_coverage_micro: number
  unanswerable_questions: number
  correct_abstentions: number
  correct_abstention_rate: number
}

export interface GenerationSummary {
  dataset: DatasetInfo
  generation_model: string
  judge_model: string
  configurations: GenerationRow[]
  token_usage: { prompt_tokens: number; completion_tokens: number; total_tokens: number }
  total_model_latency_ms: number
  model_calls: number
  usage_note: string
}

export interface CitationSummary {
  note: string
  failure_instances: number
  corrected_instances: number
  remaining_unsupported_instances: number
  patterns: { pattern_id: string; question_id: string; action: string; instances: number; corrected_instances: number; status: string; reason: string }[]
  human_review: { pattern_id: string; status: string; instances: number; recommendation_file: string }
}

export interface RagasSummary {
  tool: string
  judge_model: string
  generation_config: string
  questions: number
  metrics: Record<string, { mean: number | null; scored: number; of: number }>
}

export interface RedTeamSummary {
  model: string
  direct_attacks: number
  direct_attacks_blocked: number
  benign_questions: number
  benign_questions_blocked: number
  indirect_attacks: number
  indirect_succeeded_prompt_only: number
  indirect_succeeded_with_sanitizer: number
  note: string
}

export interface ComparisonRow {
  id: string
  group: string
  source_report: string
  label: string
  candidate_pool: number | null
  final_context_size: number | null
  precision_at_3: number
  precision_at_5: number
  precision_at_10: number | null
  recall_at_3: number
  recall_at_5: number
  recall_at_10: number | null
  mrr_at_10: number
  before_mrr_at_10?: number
  latency_note: string | null
  status: string
}

export interface Comparison {
  rows: ComparisonRow[]
  limitations: string[]
  note: string
}
