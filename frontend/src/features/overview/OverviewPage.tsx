import { useQuery } from '@tanstack/react-query'
import { CheckCircle2, XCircle } from 'lucide-react'
import { Link } from 'react-router-dom'
import { EmptyState, ErrorNotice, PageHeader, Section, Skeleton, StatStrip, TableWrap } from '@/components/states'
import { Badge } from '@/components/ui/badge'
import { Page } from '@/layouts/AppLayout'
import { count, dateTime, NOT_RECORDED } from '@/lib/format'
import { api } from '@/services/api'

function Health({ ok, label, detail }: { ok: boolean; label: string; detail: string }) {
  return (
    <Badge tone={ok ? 'good' : 'bad'}>
      {ok ? <CheckCircle2 /> : <XCircle />} {label}: {detail}
    </Badge>
  )
}

export function OverviewPage() {
  const overview = useQuery({ queryKey: ['overview'], queryFn: api.overview, refetchInterval: 30_000 })
  if (overview.isLoading) return <Page><Skeleton rows={6} /></Page>
  if (overview.isError) return <Page><PageHeader title="Overview" /><ErrorNotice error={overview.error} onRetry={() => overview.refetch()} /></Page>
  const data = overview.data!
  return (
    <Page>
      <PageHeader
        title="Overview"
        actions={(
          <div className="flex flex-wrap gap-1.5">
            <Health ok={data.health.api} label="API" detail="responding" />
            <Health ok={data.health.database.ok} label="Database" detail={data.health.database.detail} />
            <Health ok={data.health.provider_configured} label="NVIDIA key" detail={data.health.provider_configured ? 'configured' : 'missing'} />
          </div>
        )}
      />
      <StatStrip items={[
        { label: 'Documents', value: count(data.counts.documents) },
        { label: 'Chunks', value: count(data.counts.chunks) },
        { label: 'Conversations', value: count(data.counts.conversations) },
        { label: 'Questions asked', value: count(data.counts.queries) },
      ]} />
      <Section title="Models in use">
        <TableWrap>
          <tbody>
            <tr><th scope="row" className="w-48">Embedding</th><td className="num">{data.models.embedding_model} ({data.models.embedding_dimensions} dimensions)</td></tr>
            <tr><th scope="row">Generation</th><td className="num">{data.models.generation_model ?? NOT_RECORDED}</td></tr>
            <tr><th scope="row">Reranker</th><td className="num">{data.models.reranker_model ?? NOT_RECORDED}</td></tr>
          </tbody>
        </TableWrap>
      </Section>
      <div className="mt-8 grid gap-8 lg:grid-cols-2 [&>section]:mt-0">
        <Section title="Recent questions">
          {data.recent_queries.length === 0
            ? <EmptyState title="No questions yet">Ask one in <Link className="text-accent underline" to="/chat">AI Chat</Link>.</EmptyState>
            : (
              <ul className="divide-y divide-line rounded-md border border-line">
                {data.recent_queries.map((item, index) => (
                  <li key={index} className="px-3 py-2">
                    <Link to={`/chat/${item.conversation_id}`} className="line-clamp-2 break-words hover:text-accent">{item.question}</Link>
                    <p className="text-xs text-ink-2">{dateTime(item.created_at)}</p>
                  </li>
                ))}
              </ul>
            )}
        </Section>
        <Section title="Recent ingestion">
          {data.recent_jobs.length === 0
            ? <EmptyState title="No uploads yet">Add a file in <Link className="text-accent underline" to="/documents">Documents</Link>.</EmptyState>
            : (
              <ul className="divide-y divide-line rounded-md border border-line">
                {data.recent_jobs.map((job) => (
                  <li key={job.id} className="flex items-center justify-between gap-3 px-3 py-2">
                    <div className="min-w-0">
                      <p className="truncate">{job.filename}</p>
                      <p className="text-xs text-ink-2">{job.kind}, {dateTime(job.finished_at ?? job.created_at)}</p>
                    </div>
                    <Badge tone={job.status === 'succeeded' ? 'good' : job.status === 'failed' ? 'bad' : 'accent'}>{job.status}</Badge>
                  </li>
                ))}
              </ul>
            )}
        </Section>
      </div>
    </Page>
  )
}
