import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ChevronRight, Lock, RefreshCw, Trash2, Upload } from 'lucide-react'
import { useRef, useState } from 'react'
import { EmptyState, ErrorNotice, PageHeader, Section, Skeleton, TableWrap } from '@/components/states'
import { ConfirmDialog } from '@/components/ui/alert-dialog'
import { Badge, type BadgeTone } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Page } from '@/layouts/AppLayout'
import { bytes, count, dateTime, NOT_RECORDED } from '@/lib/format'
import { api, ApiFailure } from '@/services/api'
import type { AppConfig, DocumentItem } from '@/types/api'

const STATUS_TONE: Record<string, BadgeTone> = {
  ready: 'good', succeeded: 'good', processing: 'accent', queued: 'accent', running: 'accent', failed: 'bad',
}

export function validateFile(file: File, limits: AppConfig['limits'] | undefined) {
  if (!limits) return null
  const extension = `.${file.name.split('.').pop()?.toLowerCase() ?? ''}`
  if (!limits.supported_types.includes(extension)) return `Supported file types: ${limits.supported_types.join(', ')}.`
  if (file.size > limits.max_upload_mb * 1024 * 1024) return `Files can be up to ${limits.max_upload_mb} MB.`
  if (file.size === 0) return 'This file is empty.'
  return null
}

function DocumentDetails({ id }: { id: number }) {
  const detail = useQuery({
    queryKey: ['document', id],
    queryFn: () => api.document(id),
    refetchInterval: (query) => (query.state.data?.jobs.some((job) => job.status === 'queued' || job.status === 'running') ? 1500 : false),
  })
  if (detail.isLoading) return <Skeleton rows={2} />
  if (detail.isError) return <ErrorNotice error={detail.error} onRetry={() => detail.refetch()} />
  const document = detail.data!
  return (
    <div className="space-y-4 py-1">
      <dl className="grid grid-cols-2 gap-x-6 gap-y-1 text-[13px] md:grid-cols-4">
        {[
          ['Version', document.version || NOT_RECORDED],
          ['Pages', document.page_count ?? NOT_RECORDED],
          ['Chunk size / overlap', document.chunk_size ? `${document.chunk_size} / ${document.chunk_overlap} tokens` : NOT_RECORDED],
          ['Uploaded', dateTime(document.created_at)],
        ].map(([label, value]) => (
          <div key={String(label)}><dt className="text-ink-2">{label}</dt><dd>{value}</dd></div>
        ))}
      </dl>
      {document.jobs.length > 0 && (
        <div>
          <h3 className="mb-1 text-[13px] font-medium text-ink-2">Processing history</h3>
          <ul className="space-y-1 text-[13px]">
            {document.jobs.map((job) => (
              <li key={job.id} className="flex flex-wrap items-center gap-2">
                <Badge tone={STATUS_TONE[job.status]}>{job.status}</Badge>
                <span>{job.kind}</span>
                <span className="text-ink-2">{dateTime(job.finished_at ?? job.created_at)}</span>
                {job.chunks_created !== null && <span className="text-ink-2">{job.chunks_created} chunks</span>}
                {job.error && <span className="text-bad">{job.error}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}
      {document.chunks.length > 0 && (
        <details>
          <summary className="text-[13px] font-medium text-ink-2">Chunks ({document.chunk_count}, showing {document.chunks.length})</summary>
          <ol className="mt-2 max-h-72 space-y-2 overflow-y-auto">
            {document.chunks.map((chunk) => (
              <li key={chunk.id} className="rounded border border-line p-2 text-[13px]">
                <p className="num mb-1 text-xs text-ink-2">ID {chunk.id}{chunk.page_number !== null && ` · page ${chunk.page_number}`}</p>
                <p className="whitespace-pre-wrap break-words">{chunk.content}</p>
              </li>
            ))}
          </ol>
        </details>
      )}
    </div>
  )
}

function DocumentRow({ document, expanded, onToggle, onChanged }: { document: DocumentItem; expanded: boolean; onToggle: () => void; onChanged: () => void }) {
  const reindex = useMutation({ mutationFn: () => api.reindex(document.id), onSuccess: onChanged })
  const remove = useMutation({ mutationFn: () => api.deleteDocument(document.id), onSuccess: onChanged })
  const error = reindex.error ?? remove.error
  const busy = document.status === 'processing'
  return (
    <>
      <tr>
        <td className="max-w-80">
          <button type="button" aria-expanded={expanded} onClick={onToggle} className="flex min-w-0 items-center gap-1.5 text-left font-medium hover:text-accent">
            <ChevronRight className={`size-4 shrink-0 transition-transform duration-150 ${expanded ? 'rotate-90' : ''}`} />
            <span className="truncate">{document.filename}</span>
            {document.is_protected && <Lock className="size-3.5 shrink-0 text-ink-2" aria-label="Protected baseline" />}
          </button>
          {document.error && <p className="mt-0.5 pl-5 text-bad">{document.error}</p>}
        </td>
        <td><Badge tone={STATUS_TONE[document.status]}>{document.status}</Badge></td>
        <td className="num">{count(document.chunk_count)}</td>
        <td className="num whitespace-nowrap">{bytes(document.size_bytes)}</td>
        <td className="whitespace-nowrap">{dateTime(document.indexed_at)}</td>
        <td>
          <div className="flex justify-end gap-1">
            {!document.is_protected && (
              <>
                <Button size="sm" variant="ghost" disabled={busy || reindex.isPending} onClick={() => reindex.mutate()}><RefreshCw /> Re-index</Button>
                <ConfirmDialog
                  trigger={<Button size="icon" variant="ghost" disabled={busy} aria-label={`Delete ${document.filename}`}><Trash2 /></Button>}
                  title={`Delete ${document.filename}?`}
                  description="Its chunks leave search immediately. Past answers keep their saved evidence. This can't be undone."
                  confirmLabel="Delete document"
                  onConfirm={() => remove.mutate()}
                />
              </>
            )}
          </div>
        </td>
      </tr>
      {error && <tr><td colSpan={6}><ErrorNotice error={error} /></td></tr>}
      {expanded && <tr><td colSpan={6} className="bg-panel/50"><DocumentDetails id={document.id} /></td></tr>}
    </>
  )
}

export function DocumentsPage() {
  const queryClient = useQueryClient()
  const input = useRef<HTMLInputElement>(null)
  const [progress, setProgress] = useState<number | null>(null)
  const [localError, setLocalError] = useState<string | null>(null)
  const [expanded, setExpanded] = useState<number | null>(null)
  const [dragging, setDragging] = useState(false)

  const config = useQuery({ queryKey: ['config'], queryFn: api.config })
  const documents = useQuery({
    queryKey: ['documents'],
    queryFn: api.documents,
    refetchInterval: (query) => (query.state.data?.some((item) => item.status === 'processing') ? 1500 : false),
  })

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ['documents'] })
    queryClient.invalidateQueries({ queryKey: ['document'] })
  }

  const upload = useMutation({
    mutationFn: (file: File) => api.upload(file, setProgress),
    onSuccess: (result) => { setExpanded(result.document_id); refresh() },
    onSettled: () => setProgress(null),
  })

  const choose = (file: File | undefined) => {
    if (!file) return
    const problem = validateFile(file, config.data?.limits)
    setLocalError(problem)
    upload.reset()
    if (!problem) upload.mutate(file)
  }

  const limits = config.data?.limits
  const failure = upload.error as ApiFailure | null

  return (
    <Page>
      <PageHeader title="Documents" description="Upload files to search them in chat. Uploading a file with an existing name replaces that document once the new version is ready." />
      <div
        onDragOver={(event) => { event.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => { event.preventDefault(); setDragging(false); choose(event.dataTransfer.files[0]) }}
        className={`flex flex-wrap items-center justify-between gap-3 rounded-md border border-dashed px-4 py-4 transition-colors duration-150 ${dragging ? 'border-accent bg-accent-soft' : 'border-line-strong'}`}
      >
        <div>
          <p className="font-medium">Drop a file here, or choose one</p>
          <p className="text-[13px] text-ink-2">
            {limits ? `${limits.supported_types.join(', ')} up to ${limits.max_upload_mb} MB. PDFs up to ${limits.max_pdf_pages} pages.` : 'Loading limits'}
          </p>
        </div>
        <input
          ref={input}
          type="file"
          aria-label="Choose a document"
          className="sr-only"
          accept={limits?.supported_types.join(',')}
          onChange={(event) => { choose(event.target.files?.[0]); event.target.value = '' }}
        />
        <Button variant="primary" disabled={upload.isPending} onClick={() => input.current?.click()}><Upload /> Choose file</Button>
        {progress !== null && (
          <div className="w-full">
            <div role="progressbar" aria-label="Upload progress" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100} className="h-1.5 overflow-hidden rounded bg-panel">
              <div className="h-full bg-accent transition-[width] duration-150" style={{ width: `${progress}%` }} />
            </div>
            <p className="num mt-1 text-xs text-ink-2">Uploading {progress}%</p>
          </div>
        )}
      </div>
      {localError && <div role="alert" className="mt-3 rounded-md bg-bad-soft p-3 text-sm font-medium text-bad">{localError}</div>}
      {failure && <div className="mt-3"><ErrorNotice error={failure} /></div>}

      <Section title="Indexed documents">
        {documents.isLoading && <Skeleton />}
        {documents.isError && <ErrorNotice error={documents.error} onRetry={() => documents.refetch()} />}
        {documents.data?.length === 0 && <EmptyState title="No documents yet">Upload a PDF, text or Markdown file to start.</EmptyState>}
        {!!documents.data?.length && (
          <TableWrap>
            <thead><tr><th>Name</th><th>Status</th><th>Chunks</th><th>Size</th><th>Indexed</th><th><span className="sr-only">Actions</span></th></tr></thead>
            <tbody>
              {documents.data.map((document) => (
                <DocumentRow
                  key={document.id}
                  document={document}
                  expanded={expanded === document.id}
                  onToggle={() => setExpanded(expanded === document.id ? null : document.id)}
                  onChanged={refresh}
                />
              ))}
            </tbody>
          </TableWrap>
        )}
      </Section>
    </Page>
  )
}
