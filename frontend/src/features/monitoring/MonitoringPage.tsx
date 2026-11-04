import { useQuery } from '@tanstack/react-query'
import { EmptyState, ErrorNotice, PageHeader, Section, Skeleton, StatStrip, TableWrap } from '@/components/states'
import { Badge } from '@/components/ui/badge'
import { Page } from '@/layouts/AppLayout'
import { count, dateTime, milliseconds, NOT_RECORDED } from '@/lib/format'
import { api } from '@/services/api'

export function MonitoringPage() {
  const metrics = useQuery({ queryKey: ['metrics'], queryFn: api.metrics, refetchInterval: 15_000 })
  const overview = useQuery({ queryKey: ['overview'], queryFn: api.overview })
  const config = useQuery({ queryKey: ['config'], queryFn: api.config })
  if (metrics.isLoading) return <Page><Skeleton rows={8} /></Page>
  if (metrics.isError) return <Page><PageHeader title="System Monitoring" /><ErrorNotice error={metrics.error} onRetry={() => metrics.refetch()} /></Page>
  const data = metrics.data!
  const database = overview.data?.health.database
  return (
    <Page>
      <PageHeader title="System Monitoring" description="From the request traces this server writes. Refreshes every 15 seconds." />
      <StatStrip items={[
        { label: 'Traced requests', value: count(data.requests) },
        { label: 'Blocked', value: count(data.statuses.blocked ?? 0) },
        { label: 'Errors', value: count(data.statuses.error ?? 0) },
        { label: 'Citation failures', value: count(data.citation_failures) },
        { label: 'Tokens used', value: count(data.total_tokens) },
      ]} />

      <Section title="Services">
        <TableWrap>
          <tbody>
            <tr><th scope="row" className="w-48">Backend</th><td><Badge tone="good">Responding</Badge></td></tr>
            <tr><th scope="row">Database</th><td>{database ? <Badge tone={database.ok ? 'good' : 'bad'}>{database.detail}</Badge> : NOT_RECORDED}</td></tr>
            <tr><th scope="row">Embedding</th><td className="num">{config.data ? `${config.data.embedding_model}, ${config.data.embedding_dimensions} dimensions` : NOT_RECORDED}</td></tr>
            <tr><th scope="row">Generation model</th><td className="num">{config.data?.generation_model ?? NOT_RECORDED}</td></tr>
            <tr><th scope="row">Reranker</th><td className="num">{config.data?.reranker_model ?? NOT_RECORDED}</td></tr>
          </tbody>
        </TableWrap>
      </Section>

      <Section title="Latency by stage">
        {data.requests === 0
          ? <EmptyState title="No requests traced yet">Ask a question in AI Chat to see timings.</EmptyState>
          : (
            <TableWrap>
              <thead><tr><th>Stage</th><th>p50</th><th>p95</th></tr></thead>
              <tbody>
                {Object.entries(data.latency_ms).map(([stage, value]) => (
                  <tr key={stage}><td>{stage}</td><td className="num">{milliseconds(value.p50)}</td><td className="num">{milliseconds(value.p95)}</td></tr>
                ))}
              </tbody>
            </TableWrap>
          )}
      </Section>

      <Section title="Recent errors">
        {data.recent_errors.length === 0
          ? <p className="text-ink-2">No traced request has failed.</p>
          : (
            <TableWrap>
              <thead><tr><th>Time</th><th>Error type</th><th>Trace</th></tr></thead>
              <tbody>
                {data.recent_errors.map((item) => (
                  <tr key={item.trace_id}><td className="whitespace-nowrap">{dateTime(item.started_at)}</td><td>{item.error_type ?? NOT_RECORDED}</td><td className="num break-all">{item.trace_id}</td></tr>
                ))}
              </tbody>
            </TableWrap>
          )}
      </Section>

      <Section title="Ingestion jobs">
        {data.ingestion_jobs.length === 0
          ? <p className="text-ink-2">No ingestion jobs yet.</p>
          : (
            <TableWrap>
              <thead><tr><th>File</th><th>Kind</th><th>Status</th><th>Chunks</th><th>Finished</th></tr></thead>
              <tbody>
                {data.ingestion_jobs.map((job) => (
                  <tr key={job.id}>
                    <td className="max-w-72 truncate">{job.filename}</td>
                    <td>{job.kind}</td>
                    <td><Badge tone={job.status === 'succeeded' ? 'good' : job.status === 'failed' ? 'bad' : 'accent'}>{job.status}</Badge></td>
                    <td className="num">{job.chunks_created ?? NOT_RECORDED}</td>
                    <td className="whitespace-nowrap">{dateTime(job.finished_at)}</td>
                  </tr>
                ))}
              </tbody>
            </TableWrap>
          )}
      </Section>

      <Section title="Not collected">
        <p className="mb-1 text-ink-2">This server does not measure the following, so they are not shown:</p>
        <ul className="list-disc pl-5 text-ink-2">{data.not_collected.map((item) => <li key={item}>{item}</li>)}</ul>
      </Section>
    </Page>
  )
}
