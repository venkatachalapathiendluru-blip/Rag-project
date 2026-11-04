import ReactMarkdown from 'react-markdown'
import rehypeHighlight from 'rehype-highlight'
import remarkGfm from 'remark-gfm'
import type { Citation } from '@/types/api'
import { linkCitations } from './citations'

export function AnswerMarkdown({
  content, citations, selected, onSelect,
}: {
  content: string
  citations: Citation[]
  selected: number | null
  onSelect: (citation: Citation) => void
}) {
  return (
    <div className="prose-answer">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          a({ href, children }) {
            const match = href?.match(/^#cite-(\d+)$/)
            if (!match) return <a href={href} target="_blank" rel="noreferrer noopener">{children}</a>
            const citation = citations.find((item) => String(item.chunk_id) === match[1])
            if (!citation) {
              return <span className="num rounded bg-bad-soft px-1 text-xs text-bad" title="This chunk was not in the retrieved evidence">{match[1]}?</span>
            }
            return (
              <button
                type="button"
                onClick={() => onSelect(citation)}
                aria-pressed={selected === citation.chunk_id}
                aria-label={`Show evidence for chunk ${citation.chunk_id}`}
                className="num mx-0.5 rounded bg-accent-soft px-1 align-baseline text-xs font-medium text-accent transition-colors duration-150 hover:bg-accent hover:text-on-accent aria-pressed:bg-accent aria-pressed:text-on-accent"
              >
                {citation.chunk_id}
              </button>
            )
          },
        }}
      >
        {linkCitations(content)}
      </ReactMarkdown>
    </div>
  )
}
