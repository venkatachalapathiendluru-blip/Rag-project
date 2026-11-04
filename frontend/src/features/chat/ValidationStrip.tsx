import { AlertTriangle, CheckCircle2, CircleSlash, ShieldAlert } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import type { AnswerStatus, Validation } from '@/types/api'

/** Citation-ID validity and grounding stay separate because they answer different questions. */
export function ValidationStrip({ status, validation }: { status: AnswerStatus | null; validation: Validation | null }) {
  if (!validation) {
    return <p className="mt-2 text-xs text-ink-3">Saved before validation details were stored.</p>
  }

  const items = []

  if (status === 'blocked') {
    items.push(<Badge key="blocked" tone="warn"><ShieldAlert /> Blocked by guardrail</Badge>)
  }
  if (status === 'no_documents') {
    items.push(<Badge key="none"><CircleSlash /> No matching documents, model not called</Badge>)
  }
  if (validation.citation_ids_valid === true) {
    items.push(<Badge key="ids" tone="good"><CheckCircle2 /> Citation IDs valid</Badge>)
  } else if (validation.invalid_ids.length > 0) {
    items.push(<Badge key="ids" tone="bad"><AlertTriangle /> Unknown citation IDs: {validation.invalid_ids.join(', ')}</Badge>)
  } else if (status === 'no_evidence_cited') {
    items.push(<Badge key="ids" tone="warn"><AlertTriangle /> No evidence cited</Badge>)
  }
  if (validation.grounding_status === 'EVALUATED') {
    items.push(validation.grounded
      ? <Badge key="grounded" tone="good"><CheckCircle2 /> Grounding check passed</Badge>
      : <Badge key="grounded" tone="bad"><AlertTriangle /> Grounding check failed</Badge>)
  } else if (validation.grounding_status === 'NOT_VALIDATED') {
    items.push(<Badge key="grounded" tone="warn"><AlertTriangle /> Grounding check unavailable</Badge>)
  }
  if (validation.rerank_status === 'failed_used_retrieval_order') {
    items.push(<Badge key="rerank" tone="warn"><AlertTriangle /> Reranker failed, retrieval order used</Badge>)
  }
  if (validation.retrieval_mode === 'vector_fallback') {
    items.push(<Badge key="mode" tone="warn"><AlertTriangle /> Keyword search failed, vector only</Badge>)
  }
  if (validation.flagged_chunk_ids.length > 0) {
    items.push(<Badge key="flag" tone="warn"><ShieldAlert /> Instruction-like text removed from {validation.flagged_chunk_ids.length} source(s)</Badge>)
  }

  return (
    <div className="mt-2">
      {items.length > 0 && <div className="flex flex-wrap gap-1.5">{items}</div>}
      {validation.unsupported_claims.length > 0 && (
        <details className="mt-1.5 text-[13px] text-ink-2">
          <summary>Claims the check could not support ({validation.unsupported_claims.length})</summary>
          <ul className="mt-1 list-disc pl-5">
            {validation.unsupported_claims.map((claim) => <li key={claim}>{claim}</li>)}
          </ul>
        </details>
      )}
    </div>
  )
}
