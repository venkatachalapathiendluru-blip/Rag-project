import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { api, ApiFailure } from '@/services/api'
import { assistantMessage, citation, config, validation } from '@/test/fixtures'
import { renderPage } from '@/test/utils'
import { AnswerMarkdown } from './AnswerMarkdown'
import { ChatPage } from './ChatPage'
import { linkCitations } from './citations'
import { ValidationStrip } from './ValidationStrip'

function stubBase() {
  vi.spyOn(api, 'config').mockResolvedValue(config)
  vi.spyOn(api, 'documents').mockResolvedValue([])
  vi.spyOn(api, 'conversations').mockResolvedValue([])
}

describe('linkCitations', () => {
  it('links single and grouped citations and leaves other text alone', () => {
    expect(linkCitations('A [Chunk ID: 1].')).toBe('A [1](#cite-1).')
    expect(linkCitations('[Chunk ID: 1, Chunk ID: 2]')).toBe('[1](#cite-1) [2](#cite-2)')
    expect(linkCitations('[see notes] and [1]')).toBe('[see notes] and [1]')
  })
})

describe('AnswerMarkdown', () => {
  it('opens evidence for a real citation', async () => {
    const onSelect = vi.fn()
    renderPage(<AnswerMarkdown content="Yes [Chunk ID: 12]." citations={[citation]} selected={null} onSelect={onSelect} />)
    await userEvent.click(screen.getByRole('button', { name: /evidence for chunk 12/i }))
    expect(onSelect).toHaveBeenCalledWith(citation)
  })

  it('never makes an invented citation clickable', () => {
    renderPage(<AnswerMarkdown content="Yes [Chunk ID: 99]." citations={[citation]} selected={null} onSelect={vi.fn()} />)
    expect(screen.queryByRole('button')).toBeNull()
    expect(screen.getByText('99?')).toBeInTheDocument()
  })

  it('renders markdown and does not render raw HTML', () => {
    const { container } = renderPage(<AnswerMarkdown content={'**bold** <img src=x onerror=alert(1)>\n\n```python\nprint(1)\n```'} citations={[]} selected={null} onSelect={vi.fn()} />)
    expect(container.querySelector('strong')).toHaveTextContent('bold')
    expect(container.querySelector('img')).toBeNull()
    expect(container.querySelector('code.hljs, code.language-python')).not.toBeNull()
  })
})

describe('ValidationStrip', () => {
  it('reports citation validity and grounding separately', () => {
    renderPage(<ValidationStrip status="answered" validation={{ ...validation, grounded: false, unsupported_claims: ['Claim X'] }} />)
    expect(screen.getByText(/Citation IDs valid/)).toBeInTheDocument()
    expect(screen.getByText(/Grounding check failed/)).toBeInTheDocument()
    expect(screen.getByText('Claim X')).toBeInTheDocument()
  })

  it('states a reranker fallback openly', () => {
    renderPage(<ValidationStrip status="answered" validation={{ ...validation, rerank_status: 'failed_used_retrieval_order' }} />)
    expect(screen.getByText(/Reranker failed/)).toBeInTheDocument()
  })

  it('explains older messages without details', () => {
    renderPage(<ValidationStrip status={null} validation={null} />)
    expect(screen.getByText(/before validation details/)).toBeInTheDocument()
  })
})

describe('ChatPage', () => {
  it('opens the source panel with real chunk metadata', async () => {
    stubBase()
    vi.spyOn(api, 'conversation').mockResolvedValue({ id: 5, title: 't', created_at: '', updated_at: '', messages: [assistantMessage] })
    renderPage(<ChatPage />, { path: '/chat/:conversationId', route: '/chat/5' })
    await userEvent.click(await screen.findByRole('button', { name: /evidence for chunk 12/i }))
    const panel = screen.getByRole('complementary', { name: 'Source evidence' })
    expect(panel).toHaveTextContent('policy.pdf')
    expect(panel).toHaveTextContent('Refunds are issued within 30 days.')
    expect(panel).toHaveTextContent('3.2000')
  })

  it('shows "Not recorded" for a missing page, not an invented number', async () => {
    stubBase()
    const message = { ...assistantMessage, citations: [{ ...citation, page_number: null }] }
    vi.spyOn(api, 'conversation').mockResolvedValue({ id: 5, title: 't', created_at: '', updated_at: '', messages: [message] })
    renderPage(<ChatPage />, { path: '/chat/:conversationId', route: '/chat/5' })
    await userEvent.click(await screen.findByRole('button', { name: /evidence for chunk 12/i }))
    expect(screen.getByRole('complementary', { name: 'Source evidence' })).toHaveTextContent('Not recorded')
  })

  it('sends a follow-up in the same conversation', async () => {
    stubBase()
    vi.spyOn(api, 'conversation').mockResolvedValue({ id: 5, title: 't', created_at: '', updated_at: '', messages: [] })
    const chat = vi.spyOn(api, 'chat').mockResolvedValue({ conversation_id: 5 } as never)
    renderPage(<ChatPage />, { path: '/chat/:conversationId', route: '/chat/5' })
    await userEvent.type(screen.getByLabelText('Your question'), 'And then?{Enter}')
    await waitFor(() => expect(chat).toHaveBeenCalled())
    expect(chat.mock.calls[0][0]).toMatchObject({ question: 'And then?', conversation_id: 5 })
  })

  it('keeps the question and offers retry when the provider fails', async () => {
    stubBase()
    vi.spyOn(api, 'chat').mockRejectedValue(new ApiFailure('The language model timed out. Try again.', 'model_timeout', 504, 'req1', null))
    renderPage(<ChatPage />, { path: '/chat', route: '/chat' })
    await userEvent.type(screen.getByLabelText('Your question'), 'Hello{Enter}')
    expect(await screen.findByRole('alert')).toHaveTextContent('timed out')
    expect(screen.getByLabelText('Your question')).toHaveValue('Hello')
    expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument()
  })

  it('guides the user when nothing is indexed', async () => {
    stubBase()
    renderPage(<ChatPage />, { path: '/chat', route: '/chat' })
    expect(await screen.findByText('Nothing is indexed yet')).toBeInTheDocument()
  })

  it('disables Ask for an empty question', async () => {
    stubBase()
    renderPage(<ChatPage />, { path: '/chat', route: '/chat' })
    expect(screen.getByRole('button', { name: 'Ask' })).toBeDisabled()
  })
})
