import { Badge, type BadgeTone } from '@/components/ui/badge'
import type { EvaluationLabel } from '@/types/api'

const LABELS: Record<EvaluationLabel, { text: string; tone: BadgeTone }> = {
  ORIGINAL_EVALUATION: { text: 'Original evaluation', tone: 'neutral' },
  OFFLINE_ANNOTATION_CORRECTION: { text: 'Offline annotation correction', tone: 'warn' },
  NEW_EVALUATION: { text: 'New evaluation', tone: 'accent' },
  HUMAN_APPROVED_ANNOTATION: { text: 'Human-approved annotation', tone: 'good' },
}

export function EvaluationBadge({ label }: { label: EvaluationLabel }) {
  const entry = LABELS[label]
  return <Badge tone={entry.tone}>{entry.text}</Badge>
}
