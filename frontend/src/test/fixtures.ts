import type { AppConfig, Citation, Message, Validation } from '@/types/api'

export const citation: Citation = {
  chunk_id: 12, document_id: 3, filename: 'policy.pdf', page_number: 4, chunk_index: 7,
  document_version: 2, content: 'Refunds are issued within 30 days.', similarity: 0.81, rerank_score: 3.2,
}

export const validation: Validation = {
  citation_ids_valid: true, cited_ids: ['12'], invalid_ids: [], grounding_status: 'EVALUATED', grounded: true,
  unsupported_claims: [], rerank_status: 'ok', retrieval_mode: 'hybrid', flagged_chunk_ids: [],
  input_guardrail_reasons: [], output_guardrail_reasons: [],
}

export const assistantMessage: Message = {
  id: 2, role: 'assistant', content: 'Refunds take 30 days [Chunk ID: 12].', created_at: '2026-11-03T10:00:00Z',
  status: 'answered', citations: [citation], validation, profile_id: 'rrf3_1_top10', trace_id: 't',
}

export const config: AppConfig = {
  embedding_model: 'all-MiniLM-L6-v2', embedding_dimensions: 384, generation_model: 'gen', reranker_model: 'rerank',
  profiles: [{ id: 'rrf3_1_top10', label: 'RRF 3:1', mode: 'rrf', depth: 10, candidate_k: 18, vector_weight: 3, keyword_weight: 1, status: 'current_default', evidence: 'Evidence text' }],
  settings: { default_profile_id: 'rrf3_1_top10', rerank_enabled: true, final_context_k: 3, chunk_size: 180, chunk_overlap: 35, grounding_check: true },
  limits: { max_upload_mb: 20, max_pdf_pages: 500, supported_types: ['.pdf', '.txt', '.md'], history_window_messages: 6, settings_ranges: { final_context_k: [1, 10], chunk_size: [50, 240], chunk_overlap: [0, 100] } },
  security: { api_token_required: false, provider_configured: true },
  streaming_supported: false,
}
