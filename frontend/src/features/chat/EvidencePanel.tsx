import { X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { metric, NOT_RECORDED } from '@/lib/format'
import type { Citation } from '@/types/api'

export function EvidencePanel({ citation, onClose }: { citation: Citation; onClose: () => void }) {
  const facts: [string, string][] = [
    ['Document', citation.filename],
    ['Chunk ID', String(citation.chunk_id)],
    ['Page', citation.page_number === null ? NOT_RECORDED : String(citation.page_number)],
    ['Position', `Chunk ${citation.chunk_index + 1}, version ${citation.document_version}`],
    ['Similarity', metric(citation.similarity)],
    ['Rerank score', citation.rerank_score === null ? 'Not reranked' : metric(citation.rerank_score)],
  ]
  return (
    <aside aria-label="Source evidence" className="fixed inset-x-0 bottom-0 z-40 flex max-h-[75vh] flex-col border-t border-line bg-raised shadow-[0_-8px_24px_rgb(0_0_0/0.14)] xl:static xl:z-auto xl:max-h-none xl:w-[24rem] xl:shrink-0 xl:border-l xl:border-t-0 xl:bg-panel xl:shadow-none">
      <div className="flex h-12 shrink-0 items-center justify-between border-b border-line pl-4 pr-2">
        <h2>Source evidence</h2>
        <Button variant="ghost" size="icon" aria-label="Close source evidence" onClick={onClose}><X /></Button>
      </div>
      <div className="overflow-y-auto p-4">
        <dl className="grid grid-cols-[6rem_1fr] gap-x-3 gap-y-1.5 text-[13px]">
          {facts.map(([label, value]) => (
            <div key={label} className="contents">
              <dt className="text-ink-2">{label}</dt>
              <dd className="min-w-0 break-words">{value}</dd>
            </div>
          ))}
        </dl>
        <h3 className="mb-1.5 mt-4 text-[13px] font-medium text-ink-2">Chunk text</h3>
        <blockquote className="whitespace-pre-wrap break-words rounded-md border border-line bg-raised p-3 leading-relaxed">{citation.content}</blockquote>
      </div>
    </aside>
  )
}
