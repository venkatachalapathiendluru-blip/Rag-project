import { useQuery } from '@tanstack/react-query'
import { ErrorNotice, PageHeader, Section, Skeleton, StatStrip, TableWrap } from '@/components/states'
import { MetricBars } from '@/components/MetricBars'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Page } from '@/layouts/AppLayout'
import { count, dateTime, metric, milliseconds, NOT_RECORDED } from '@/lib/format'
import { api } from '@/services/api'
import type {
  CitationSummary, DatasetInfo, Evaluation, GenerationSummary, RagasSummary, RedTeamSummary, RetrievalSummary,
} from '@/types/api'
import { EvaluationBadge } from './labels'

function Frame<S>({ id, children }: { id: string; children: (summary: S, evaluation: Evaluation<S>) => React.ReactNode }) {
  const query = useQuery({ queryKey: ['evaluation', id], queryFn: () => api.evaluation<S>(id) })
  if (query.isLoading) return <Skeleton />
  if (query.isError) return <ErrorNotice error={query.error} onRetry={() => query.refetch()} />
  const evaluation = query.data!
  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-2 text-[13px] text-ink-2">
        <EvaluationBadge label={evaluation.label} />
        <span>{evaluation.title}</span>
        <span>· Run {dateTime(evaluation.generated_at)}</span>
        <span className="num">· {evaluation.file}</span>
      </div>
      {evaluation.summary === null
        ? <p role="status" className="rounded-md bg-panel p-3">The report file is not available on this server, so no results are shown.</p>
        : children(evaluation.summary, evaluation)}
    </div>
  )
}

function Dataset({ dataset }: { dataset: DatasetInfo }) {
  return (
    <StatStrip items={[
      { label: 'Questions', value: count(dataset.question_count) },
      { label: 'Answerable', value: count(dataset.answerable_count) },
      { label: 'Unanswerable', value: count(dataset.unanswerable_count) },
      { label: 'Review status', value: <span className="text-sm">{dataset.review_status}</span> },
    ]} />
  )
}

function Retrieval() {
  return (
    <Frame<RetrievalSummary> id="retrieval_top18">
      {(summary) => (
        <>
          <Dataset dataset={summary.dataset} />
          <Section title="MRR@10 by configuration" description={`Scope: ${summary.scope}.`}>
            <MetricBars metricName="MRR@10" data={summary.configurations.map((row) => ({ label: row.label, value: row.mrr_at_10 }))} />
          </Section>
          <Section title="All retrieval metrics">
            <TableWrap>
              <thead><tr><th>Configuration</th><th>P@3</th><th>P@5</th><th>P@10</th><th>R@3</th><th>R@5</th><th>R@10</th><th>MRR@10</th></tr></thead>
              <tbody>
                {summary.configurations.map((row) => (
                  <tr key={row.id}>
                    <td className="font-medium">{row.label}</td>
                    {[row.precision_at_3, row.precision_at_5, row.precision_at_10, row.recall_at_3, row.recall_at_5, row.recall_at_10, row.mrr_at_10].map((value, index) => (
                      <td key={index} className="num">{metric(value)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </TableWrap>
          </Section>
          <Section title="Mean retrieval latency" description="Measured during the benchmark, on one machine.">
            <StatStrip items={[
              { label: 'Vector search', value: milliseconds(summary.latency_ms.vector_mean) },
              { label: 'Keyword search', value: milliseconds(summary.latency_ms.keyword_mean) },
            ]} />
          </Section>
          <Section title="RRF 3:1 questions below full recall at 5" description="Questions where at least one relevant chunk was outside the top 5.">
            <TableWrap>
              <thead><tr><th>ID</th><th>Question</th><th>Relevant</th><th>Top 5</th><th>R@5</th></tr></thead>
              <tbody>
                {summary.rrf_3_1_questions_below_full_recall_at_5.map((row) => (
                  <tr key={row.question_id}>
                    <td className="num whitespace-nowrap">{row.question_id}</td>
                    <td className="min-w-64">{row.question}</td>
                    <td className="num">{row.relevant_chunk_ids.join(', ')}</td>
                    <td className="num whitespace-nowrap">{row.retrieved_top5.join(', ')}</td>
                    <td className="num">{metric(row.recall_at_5)}</td>
                  </tr>
                ))}
              </tbody>
            </TableWrap>
          </Section>
        </>
      )}
    </Frame>
  )
}

function Generation() {
  return (
    <div className="space-y-10">
      <GenerationReport id="generation_live_depth" />
      <GenerationReport id="generation" />
    </div>
  )
}

function GenerationReport({ id }: { id: string }) {
  return (
    <Frame<GenerationSummary> id={id}>
      {(summary) => (
        <>
          <Dataset dataset={summary.dataset} />
          <Section title="Judge-scored quality, top 3 context" description={`Generation model and judge: ${summary.generation_model}. Faithfulness, citation-ID validity and citation support are separate measures.`}>
            <TableWrap>
              <thead><tr><th>Configuration</th><th>Faithfulness (micro / macro)</th><th>Relevancy (1 to 5)</th><th>Citation-ID validity</th><th>Citation support (micro / macro)</th><th>Expected points</th><th>Correct abstention</th></tr></thead>
              <tbody>
                {summary.configurations.map((row) => (
                  <tr key={row.id}>
                    <td className="min-w-48 font-medium">{row.label}</td>
                    <td className="num">{metric(row.faithfulness_micro)} / {metric(row.faithfulness_macro)}</td>
                    <td className="num">{metric(row.answer_relevancy_mean)}</td>
                    <td className="num">{metric(row.citation_id_validity_micro)}</td>
                    <td className="num">{metric(row.citation_support_micro)} / {metric(row.citation_support_macro)}</td>
                    <td className="num">{metric(row.expected_point_coverage_micro)}</td>
                    <td className="num">{row.correct_abstentions}/{row.unanswerable_questions}</td>
                  </tr>
                ))}
              </tbody>
            </TableWrap>
          </Section>
          <Section title="Model usage for this evaluation" description={summary.usage_note}>
            <StatStrip items={[
              { label: 'Model calls', value: count(summary.model_calls) },
              { label: 'Total tokens', value: count(summary.token_usage.total_tokens) },
              { label: 'Prompt tokens', value: count(summary.token_usage.prompt_tokens) },
              { label: 'Completion tokens', value: count(summary.token_usage.completion_tokens) },
              { label: 'Model time', value: milliseconds(summary.total_model_latency_ms) },
            ]} />
          </Section>
        </>
      )}
    </Frame>
  )
}

function Citations() {
  return (
    <Frame<CitationSummary> id="citation_corrections">
      {(summary) => (
        <>
          <p className="mb-4 max-w-[75ch] rounded-md bg-warn-soft p-3 text-warn">{summary.note}</p>
          <StatStrip items={[
            { label: 'Failure instances reviewed', value: count(summary.failure_instances) },
            { label: 'Corrected by annotation', value: count(summary.corrected_instances) },
            { label: 'Still unsupported', value: count(summary.remaining_unsupported_instances) },
          ]} />
          <Section title="Human decision" aside={<Badge tone="warn">{summary.human_review.status}</Badge>}>
            <p className="max-w-[75ch]">{summary.human_review.pattern_id} covers {summary.human_review.instances} instances. A recommendation is in <span className="num">{summary.human_review.recommendation_file}</span>, but it has not been approved, so no human-approved results exist yet.</p>
          </Section>
          <Section title="Correction patterns">
            <TableWrap>
              <thead><tr><th>Pattern</th><th>Question</th><th>Status</th><th>Corrected</th><th>Reason</th></tr></thead>
              <tbody>
                {summary.patterns.map((row) => (
                  <tr key={row.pattern_id}>
                    <td className="num">{row.pattern_id}</td>
                    <td className="num whitespace-nowrap">{row.question_id}</td>
                    <td><Badge tone={row.status === 'CORRECTED' ? 'neutral' : 'warn'}>{row.status}</Badge></td>
                    <td className="num">{row.corrected_instances}/{row.instances}</td>
                    <td className="min-w-72">{row.reason}</td>
                  </tr>
                ))}
              </tbody>
            </TableWrap>
          </Section>
        </>
      )}
    </Frame>
  )
}

function Ragas() {
  const names: Record<string, string> = {
    faithfulness: 'Faithfulness',
    context_recall: 'Context recall',
    llm_context_precision_with_reference: 'Context precision',
  }
  return (
    <Frame<RagasSummary> id="ragas">
      {(summary) => (
        <>
          <p className="mb-4 max-w-[75ch] text-ink-2">Scored on saved answers from configuration {summary.generation_config}. The judge, {summary.judge_model}, is the same model that wrote the answers.</p>
          <TableWrap>
            <thead><tr><th>Metric</th><th>Mean</th><th>Questions scored</th></tr></thead>
            <tbody>
              {Object.entries(summary.metrics).map(([key, value]) => (
                <tr key={key}>
                  <td className="font-medium">{names[key] ?? key}</td>
                  <td className="num">{metric(value.mean)}</td>
                  <td className="num">{value.scored}/{value.of}</td>
                </tr>
              ))}
            </tbody>
          </TableWrap>
        </>
      )}
    </Frame>
  )
}

function RedTeam() {
  return (
    <Frame<RedTeamSummary> id="red_team">
      {(summary) => (
        <>
          <p className="mb-4 max-w-[75ch] rounded-md bg-warn-soft p-3 text-warn">{summary.note}</p>
          <StatStrip items={[
            { label: 'Direct attacks blocked', value: `${summary.direct_attacks_blocked}/${summary.direct_attacks}` },
            { label: 'Normal questions blocked', value: `${summary.benign_questions_blocked}/${summary.benign_questions}` },
            { label: 'Indirect attacks that worked, sanitizer on', value: `${summary.indirect_succeeded_with_sanitizer}/${summary.indirect_attacks}` },
            { label: 'Indirect attacks that worked, prompt only', value: `${summary.indirect_succeeded_prompt_only}/${summary.indirect_attacks}` },
          ]} />
        </>
      )}
    </Frame>
  )
}

export function EvaluationPage() {
  const limits = useQuery({ queryKey: ['evaluation', 'generation'], queryFn: () => api.evaluation('generation') })
  return (
    <Page>
      <PageHeader title="Evaluation" description="Saved results from past runs. Opening this page runs nothing and calls no model." />
      <Tabs defaultValue="retrieval">
        <TabsList aria-label="Evaluation reports">
          <TabsTrigger value="retrieval">Retrieval</TabsTrigger>
          <TabsTrigger value="generation">Generation</TabsTrigger>
          <TabsTrigger value="citations">Citation corrections</TabsTrigger>
          <TabsTrigger value="ragas">RAGAS</TabsTrigger>
          <TabsTrigger value="redteam">Red team</TabsTrigger>
        </TabsList>
        <div className="pt-5">
          <TabsContent value="retrieval"><Retrieval /></TabsContent>
          <TabsContent value="generation"><Generation /></TabsContent>
          <TabsContent value="citations"><Citations /></TabsContent>
          <TabsContent value="ragas"><Ragas /></TabsContent>
          <TabsContent value="redteam"><RedTeam /></TabsContent>
        </div>
      </Tabs>
      <Section title="How to read these results">
        <ul className="max-w-[75ch] list-disc space-y-1 pl-5 text-ink-2">
          {(limits.data?.limitations ?? []).map((item) => <li key={item}>{item}</li>)}
          {limits.isError && <li>{NOT_RECORDED}</li>}
        </ul>
      </Section>
    </Page>
  )
}
