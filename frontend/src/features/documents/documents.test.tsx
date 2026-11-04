import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { api, ApiFailure } from '@/services/api'
import { config } from '@/test/fixtures'
import { renderPage } from '@/test/utils'
import type { DocumentItem } from '@/types/api'
import { DocumentsPage, validateFile } from './DocumentsPage'

const base: DocumentItem = {
  id: 1, filename: 'guide.pdf', media_type: 'application/pdf', size_bytes: 2048, page_count: 2, version: 1,
  status: 'ready', error: null, chunk_size: 180, chunk_overlap: 35, chunk_count: 9, is_protected: false,
  created_at: '2026-11-03T10:00:00Z', updated_at: '2026-11-03T10:00:00Z', indexed_at: '2026-11-03T10:00:00Z',
}

function stub(documents: DocumentItem[]) {
  vi.spyOn(api, 'config').mockResolvedValue(config)
  vi.spyOn(api, 'documents').mockResolvedValue(documents)
}

describe('validateFile', () => {
  it('rejects wrong types, oversized files and empty files', () => {
    expect(validateFile(new File(['x'], 'a.exe'), config.limits)).toMatch(/Supported/)
    expect(validateFile(new File([], 'a.pdf'), config.limits)).toMatch(/empty/)
    const big = new File(['x'], 'a.pdf')
    Object.defineProperty(big, 'size', { value: 21 * 1024 * 1024 })
    expect(validateFile(big, config.limits)).toMatch(/20 MB/)
    expect(validateFile(new File(['x'], 'A.PDF'), config.limits)).toBeNull()
  })
})

describe('DocumentsPage', () => {
  it('lists documents with their real status and chunk count', async () => {
    stub([base, { ...base, id: 2, filename: 'bad.pdf', status: 'failed', error: 'No text could be extracted.', chunk_count: 0 }])
    renderPage(<DocumentsPage />)
    const row = (await screen.findByText('guide.pdf')).closest('tr')!
    expect(within(row).getByText('ready')).toBeInTheDocument()
    expect(within(row).getByText('9')).toBeInTheDocument()
    expect(screen.getByText('No text could be extracted.')).toBeInTheDocument()
  })

  it('does not upload an invalid file', async () => {
    stub([])
    const upload = vi.spyOn(api, 'upload')
    renderPage(<DocumentsPage />)
    await screen.findByText(/up to 20 MB/)
    await userEvent.upload(screen.getByLabelText('Choose a document'), new File(['x'], 'a.exe'), { applyAccept: false })
    expect(await screen.findByRole('alert')).toHaveTextContent('Supported file types')
    expect(upload).not.toHaveBeenCalled()
  })

  it('uploads a valid file and shows a duplicate error from the server', async () => {
    stub([])
    vi.spyOn(api, 'upload').mockRejectedValue(new ApiFailure('This file is already indexed as guide.pdf.', 'duplicate_document', 409, 'r', null))
    renderPage(<DocumentsPage />)
    await screen.findByText(/up to 20 MB/)
    await userEvent.upload(screen.getByLabelText('Choose a document'), new File(['x'], 'a.pdf'))
    expect(await screen.findByRole('alert')).toHaveTextContent('already indexed')
  })

  it('asks for confirmation before deleting', async () => {
    stub([base])
    const remove = vi.spyOn(api, 'deleteDocument').mockResolvedValue(undefined)
    renderPage(<DocumentsPage />)
    await userEvent.click(await screen.findByRole('button', { name: 'Delete guide.pdf' }))
    expect(remove).not.toHaveBeenCalled()
    await userEvent.click(screen.getByRole('button', { name: 'Delete document' }))
    await waitFor(() => expect(remove).toHaveBeenCalled())
    expect(remove.mock.calls[0][0]).toBe(1)
  })

  it('offers no delete or re-index on the protected baseline', async () => {
    stub([{ ...base, is_protected: true, filename: 'baseline' }])
    renderPage(<DocumentsPage />)
    await screen.findByText('baseline')
    expect(screen.queryByRole('button', { name: /delete/i })).toBeNull()
    expect(screen.queryByRole('button', { name: /re-index/i })).toBeNull()
  })

  it('shows a clear empty state', async () => {
    stub([])
    renderPage(<DocumentsPage />)
    expect(await screen.findByText('No documents yet')).toBeInTheDocument()
  })

  it('shows API failures with a retry', async () => {
    vi.spyOn(api, 'config').mockResolvedValue(config)
    vi.spyOn(api, 'documents').mockRejectedValue(new ApiFailure('The database is unavailable.', 'database_unavailable', 503, 'r', null))
    renderPage(<DocumentsPage />)
    expect(await screen.findByText('The database is unavailable.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument()
  })
})
