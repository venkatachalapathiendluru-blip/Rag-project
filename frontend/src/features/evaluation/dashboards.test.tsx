import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { ExperimentsPage } from '@/features/experiments/ExperimentsPage'
import { MonitoringPage } from '@/features/monitoring/MonitoringPage'
import { OverviewPage } from '@/features/overview/OverviewPage'
import { SettingsPage } from '@/features/settings/SettingsPage'
import { metric, milliseconds } from '@/lib/format'
import { api, ApiFailure, getToken, toApiFailure } from '@/services/api'
import { config } from '@/test/fixtures'
import { renderPage } from '@/test/utils'
import { EvaluationPage } from './EvaluationPage'

const retrievalEvaluation = {
  id: 'retrieval_top18', title: 'Retrieval benchmark', category: 'retrieval', label: 'ORIGINAL_EVALUATION', file: 'r.json',
  available: true, generated_at: '2026-11-03T00:00:00Z', limitations: ['One resume corpus of 18 chunks and 39 questions.'],
  summary: {
    dataset: { question_count: 39, answerable_count: 33, unanswerable_count: 6, review_status: 'APPROVED' },
    scope: '33 answerable questions only',
    configurations: [{ id: 'rrf_3_1', label: 'RRF 3:1', precision_at_3: 0.4646, recall_at_3: 0.798, precision_at_5: 0.3212, recall_at_5: 0.904, precision_at_10: 0.1788, recall_at_10: 0.9672, mrr_at_10: 0.9571 }],
    latency_ms: { vector_mean: null, keyword_mean: 37.5 },
    rrf_3_1_questions_below_full_recall_at_5: [],
  },
}

describe('format helpers', () => {
  it('never turns a missing value into zero', () => {
    expect(metric(null)).toBe('Not recorded')
    expect(metric(0)).toBe('0.0000')
    expect(milliseconds(undefined)).toBe('Not recorded')
  })
})

describe('EvaluationPage', () => {
  it('shows saved values, their label and limitations', async () => {
    vi.spyOn(api, 'evaluation').mockResolvedValue(retrievalEvaluation as never)
    renderPage(<EvaluationPage />)
    expect((await screen.findAllByText('0.9571')).length).toBeGreaterThan(0)
    expect(screen.getByText('Original evaluation')).toBeInTheDocument()
    expect(screen.getByText('39')).toBeInTheDocument()
    expect(screen.getByText(/One resume corpus/)).toBeInTheDocument()
    expect(screen.getByText('Not recorded')).toBeInTheDocument()
  })

  it('says a report is unavailable instead of showing zeros', async () => {
    vi.spyOn(api, 'evaluation').mockResolvedValue({ ...retrievalEvaluation, summary: null, available: false } as never)
    renderPage(<EvaluationPage />)
    expect(await screen.findByText(/not available on this server/)).toBeInTheDocument()
    expect(screen.queryByText('0.0000')).toBeNull()
  })

  it('keeps annotation corrections labelled and P013 unapproved', async () => {
    vi.spyOn(api, 'evaluation').mockImplementation((async (id: string) => (id === 'citation_corrections' ? {
      ...retrievalEvaluation, id, label: 'OFFLINE_ANNOTATION_CORRECTION',
      summary: { note: 'Not a model improvement.', failure_instances: 20, corrected_instances: 18, remaining_unsupported_instances: 2, patterns: [], human_review: { pattern_id: 'P013', status: 'NEEDS_HUMAN_APPROVAL', instances: 2, recommendation_file: 'f.md' } },
    } : retrievalEvaluation)) as never)
    renderPage(<EvaluationPage />)
    await userEvent.click(screen.getByRole('tab', { name: 'Citation corrections' }))
    expect(await screen.findByText('Offline annotation correction')).toBeInTheDocument()
    expect(screen.getByText('NEEDS_HUMAN_APPROVAL')).toBeInTheDocument()
    expect(screen.getByText(/no human-approved results exist yet/)).toBeInTheDocument()
  })
})

describe('ExperimentsPage', () => {
  it('renders saved rows only and marks missing latency', async () => {
    vi.spyOn(api, 'comparison').mockResolvedValue({
      note: 'Read from saved reports. Opening this view calls no external API.', limitations: [],
      rows: [{ id: 'x', group: 'Retrieval only', source_report: 'retrieval_top18', label: 'RRF 3:1', candidate_pool: 18, final_context_size: null, precision_at_3: 0.4646, precision_at_5: 0.3212, precision_at_10: 0.1788, recall_at_3: 0.798, recall_at_5: 0.904, recall_at_10: 0.9672, mrr_at_10: 0.9571, latency_note: null, status: 'experimental' }],
    })
    const chat = vi.spyOn(api, 'chat')
    renderPage(<ExperimentsPage />)
    expect(await screen.findByText('0.9571')).toBeInTheDocument()
    expect(screen.getByText('Experimental')).toBeInTheDocument()
    expect(screen.getByText(/calls no external API/)).toBeInTheDocument()
    expect(chat).not.toHaveBeenCalled()
  })
})

describe('OverviewPage', () => {
  it('shows counts from the API and an unhealthy database', async () => {
    vi.spyOn(api, 'overview').mockResolvedValue({
      counts: { documents: 7, chunks: 321, conversations: 4, queries: 11 }, recent_queries: [], recent_jobs: [],
      models: { embedding_model: 'mini', embedding_dimensions: 384, generation_model: null, reranker_model: 'r' },
      health: { api: true, database: { ok: false, detail: 'unreachable' }, provider_configured: true },
    })
    renderPage(<OverviewPage />)
    expect(await screen.findByText('321')).toBeInTheDocument()
    expect(screen.getByText(/Database: unreachable/)).toBeInTheDocument()
    expect(screen.getByText('Not recorded')).toBeInTheDocument()
  })
})

describe('MonitoringPage', () => {
  it('names what is not collected', async () => {
    vi.spyOn(api, 'metrics').mockResolvedValue({
      requests: 0, statuses: {}, guardrail_events: {}, citation_failures: 0, chunks_with_injection_removed: 0, total_tokens: 0,
      latency_ms: {}, recent_errors: [], recent_requests: [], ingestion_jobs: [], not_collected: ['Host memory and CPU'],
    })
    vi.spyOn(api, 'overview').mockRejectedValue(new Error('x'))
    vi.spyOn(api, 'config').mockResolvedValue(config)
    renderPage(<MonitoringPage />)
    expect(await screen.findByText('Host memory and CPU')).toBeInTheDocument()
    expect(screen.getByText('No requests traced yet')).toBeInTheDocument()
  })
})

describe('SettingsPage', () => {
  it('saves only through the API and never shows provider keys', async () => {
    vi.spyOn(api, 'config').mockResolvedValue(config)
    const save = vi.spyOn(api, 'saveSettings').mockResolvedValue(config.settings)
    const { container } = renderPage(<SettingsPage />)
    await userEvent.click(await screen.findByRole('switch', { name: 'Grounding check' }))
    await userEvent.click(screen.getByRole('button', { name: 'Save settings' }))
    await waitFor(() => expect(save).toHaveBeenCalled())
    expect(save.mock.calls[0][0]).toMatchObject({ grounding_check: false })
    expect(await screen.findByText('Settings saved.')).toBeInTheDocument()
    expect(container.textContent).not.toMatch(/nvapi-/)
  })

  it('shows server validation errors', async () => {
    vi.spyOn(api, 'config').mockResolvedValue(config)
    vi.spyOn(api, 'saveSettings').mockRejectedValue(new ApiFailure('chunk_size must be between 50 and 240.', 'invalid_setting', 422, 'r', null))
    renderPage(<SettingsPage />)
    await userEvent.click(await screen.findByRole('button', { name: 'Save settings' }))
    expect(await screen.findByText(/chunk_size must be between/)).toBeInTheDocument()
  })

  it('keeps the token in session storage', async () => {
    vi.spyOn(api, 'config').mockResolvedValue(config)
    renderPage(<SettingsPage />)
    await userEvent.type(screen.getByLabelText('Access token'), 'abc')
    await userEvent.click(screen.getByRole('button', { name: 'Save token' }))
    expect(getToken()).toBe('abc')
    sessionStorage.clear()
  })
})

describe('toApiFailure', () => {
  it('reads the API error shape', () => {
    const failure = toApiFailure({ response: { status: 409, data: { error: { code: 'duplicate_document', message: 'Dup', request_id: 'r1', details: null } } } })
    expect(failure).toMatchObject({ code: 'duplicate_document', status: 409, requestId: 'r1', message: 'Dup' })
  })

  it('explains an unreachable API', () => {
    expect(toApiFailure(new Error('Network Error')).code).toBe('network_error')
  })
})
