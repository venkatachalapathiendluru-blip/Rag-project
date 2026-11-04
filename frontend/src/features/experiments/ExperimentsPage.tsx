import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { EmptyState, ErrorNotice, PageHeader, Section, Skeleton, TableWrap } from '@/components/states'
import { MetricBars } from '@/components/MetricBars'
import { Badge, type BadgeTone } from '@/components/ui/badge'
import { Page } from '@/layouts/AppLayout'
import { metric, NOT_RECORDED } from '@/lib/format'
import { api } from '@/services/api'
import type { ComparisonRow } from '@/types/api'

const METRICS: { key: keyof ComparisonRow; label: string }[] = [
  { key: 'mrr_at_10', label: 'MRR@10' },
  { key: 'precision_at_3', label: 'P@3' },
  { key: 'recall_at_3', label: 'R@3' },
  { key: 'precision_at_5', label: 'P@5' },
  { key: 'recall_at_5', label: 'R@5' },
]

const STATUS: Record<string, { text: string; tone: BadgeTone }> = {
  provisional_default: { text: 'Provisional default, experimental', tone: 'accent' },
  comparison_baseline: { text: 'Baseline', tone: 'neutral' },
  experimental: { text: 'Experimental', tone: 'warn' },
}

function displayLabel(row: ComparisonRow) {
  return row.label.replace('->', '→').replace('Weighted ', '').replace('Vector-only', 'Vector')
    + (row.source_report === 'reranking_top10' ? ' → reranker' : '')
}

export function ExperimentsPage() {
  const [metricKey, setMetricKey] = useState<keyof ComparisonRow>('mrr_at_10')
  const comparison = useQuery({ queryKey: ['comparison'], queryFn: api.comparison })
  const rows = comparison.data?.rows ?? []
  const selected = METRICS.find((item) => item.key === metricKey)!

  return (
    <Page>
      <PageHeader title="Retrieval Experiments" description={comparison.data?.note ?? 'Comparisons from saved reports.'} />
      {comparison.isLoading && <Skeleton rows={8} />}
      {comparison.isError && <ErrorNotice error={comparison.error} onRetry={() => comparison.refetch()} />}
      {comparison.isSuccess && rows.length === 0 && <EmptyState title="No saved reports on this server">Reports are read from RAG_REPORTS_DIR.</EmptyState>}
      {rows.length > 0 && (
        <>
          <Section
            title={`${selected.label} by configuration`}
            description="The highest value on one metric does not make a configuration the best overall."
            aside={(
              <div role="group" aria-label="Metric" className="flex flex-wrap gap-1">
                {METRICS.map((item) => (
                  <button
                    key={item.key}
                    type="button"
                    aria-pressed={item.key === metricKey}
                    onClick={() => setMetricKey(item.key)}
                    className="rounded-md border border-line px-2 py-1 text-[13px] transition-colors duration-150 hover:bg-panel aria-pressed:border-accent aria-pressed:bg-accent-soft aria-pressed:text-accent"
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            )}
          >
            <MetricBars
              metricName={selected.label}
              data={rows.map((row) => ({
                label: displayLabel(row),
                value: row[metricKey] as number | null,
              }))}
            />
          </Section>
          <Section title="All configurations">
            <TableWrap>
              <thead>
                <tr><th>Configuration</th><th>Group</th><th>Status</th><th>Pool</th><th>P@3</th><th>P@5</th><th>R@3</th><th>R@5</th><th>R@10</th><th>MRR@10</th><th>MRR before rerank</th><th>Latency</th></tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id}>
                    <td className="min-w-52 font-medium">{displayLabel(row)}</td>
                    <td className="whitespace-nowrap text-ink-2">{row.group}</td>
                    <td><Badge tone={STATUS[row.status]?.tone}>{STATUS[row.status]?.text ?? row.status}</Badge></td>
                    <td className="num">{row.candidate_pool ?? NOT_RECORDED}</td>
                    <td className="num">{metric(row.precision_at_3)}</td>
                    <td className="num">{metric(row.precision_at_5)}</td>
                    <td className="num">{metric(row.recall_at_3)}</td>
                    <td className="num">{metric(row.recall_at_5)}</td>
                    <td className="num whitespace-nowrap">{metric(row.recall_at_10)}</td>
                    <td className="num">{metric(row.mrr_at_10)}</td>
                    <td className="num whitespace-nowrap">{row.before_mrr_at_10 === undefined ? 'Not applicable' : metric(row.before_mrr_at_10)}</td>
                    <td className="min-w-40 text-ink-2">{row.latency_note ?? NOT_RECORDED}</td>
                  </tr>
                ))}
              </tbody>
            </TableWrap>
          </Section>
          <Section title="Limits of these results">
            <ul className="max-w-[75ch] list-disc space-y-1 pl-5 text-ink-2">
              {comparison.data?.limitations.map((item) => <li key={item}>{item}</li>)}
            </ul>
          </Section>
        </>
      )}
    </Page>
  )
}
