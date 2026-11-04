import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { ErrorNotice, PageHeader, Section, Skeleton, TableWrap } from '@/components/states'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Page } from '@/layouts/AppLayout'
import { currentTheme, setTheme, type ThemeChoice } from '@/lib/theme'
import { api, getToken, setToken } from '@/services/api'
import type { Settings } from '@/types/api'

const fieldClass = 'h-9 w-full max-w-md rounded-md border border-line-strong bg-raised px-2.5 text-sm text-ink'

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <label className="grid gap-1 py-3 sm:grid-cols-[15rem_1fr] sm:gap-4">
      <span>
        <span className="font-medium">{label}</span>
        {hint && <span className="mt-0.5 block text-[13px] text-ink-2">{hint}</span>}
      </span>
      <span className="flex items-center">{children}</span>
    </label>
  )
}

export function SettingsPage() {
  const queryClient = useQueryClient()
  const config = useQuery({ queryKey: ['config'], queryFn: api.config })
  const [form, setForm] = useState<Settings | null>(null)
  const [theme, setThemeState] = useState<ThemeChoice>(currentTheme())
  const [token, setTokenState] = useState(getToken())
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (config.data) setForm(config.data.settings)
  }, [config.data])

  const save = useMutation({
    mutationFn: api.saveSettings,
    onSuccess: async () => {
      setSaved(true)
      await queryClient.invalidateQueries({ queryKey: ['config'] })
    },
  })

  const update = (changes: Partial<Settings>) => {
    setSaved(false)
    setForm((current) => (current ? { ...current, ...changes } : current))
  }

  const ranges = config.data?.limits.settings_ranges
  const profile = config.data?.profiles.find((item) => item.id === form?.default_profile_id)

  return (
    <Page>
      <PageHeader title="Settings" />

      <Section title="Appearance">
        <div className="divide-y divide-line">
          <Field label="Theme">
            <select
              className={fieldClass}
              value={theme}
              onChange={(event) => {
                const choice = event.target.value as ThemeChoice
                setThemeState(choice)
                setTheme(choice)
              }}
            >
              <option value="system">Match system</option>
              <option value="light">Light</option>
              <option value="dark">Dark</option>
            </select>
          </Field>
        </div>
      </Section>

      <Section title="Access token" description="Needed only when the server sets RAG_API_TOKEN. It is kept for this browser session and never written into the app.">
        <form
          className="flex max-w-xl gap-2"
          onSubmit={(event) => {
            event.preventDefault()
            setToken(token)
            queryClient.invalidateQueries()
          }}
        >
          <input aria-label="Access token" type="password" autoComplete="off" className={fieldClass} value={token} onChange={(event) => setTokenState(event.target.value)} />
          <Button type="submit">Save token</Button>
        </form>
      </Section>

      {config.isLoading && <div className="mt-8"><Skeleton rows={6} /></div>}
      {config.isError && <div className="mt-8"><ErrorNotice error={config.error} onRetry={() => config.refetch()} /></div>}
      {form && config.data && (
        <>
          <Section title="Retrieval and answers" description="The default profile changes what chat uses. Saved evaluation results stay tied to the configuration they measured.">
            <div className="divide-y divide-line">
              <Field label="Default retrieval profile" hint={profile?.evidence}>
                <select className={fieldClass} value={form.default_profile_id} onChange={(event) => update({ default_profile_id: event.target.value })}>
                  {config.data.profiles.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
                </select>
              </Field>
              <Field label="Chunks given to the model" hint={`${ranges?.final_context_k?.join(' to ')}. Benchmarks used 3.`}>
                <input type="number" className={fieldClass} value={form.final_context_k} min={ranges?.final_context_k?.[0]} max={ranges?.final_context_k?.[1]} onChange={(event) => update({ final_context_k: Number(event.target.value) })} />
              </Field>
              <Field label="Rerank with NVIDIA" hint="Each question makes one reranker call when on.">
                <Switch aria-label="Rerank with NVIDIA" checked={form.rerank_enabled} onCheckedChange={(value) => update({ rerank_enabled: value })} />
              </Field>
              <Field label="Grounding check" hint="Adds one model call per question, and more latency.">
                <Switch aria-label="Grounding check" checked={form.grounding_check} onCheckedChange={(value) => update({ grounding_check: value })} />
              </Field>
            </div>
          </Section>

          <Section title="Chunking" description="Applies to future uploads and re-indexing. The baseline corpus keeps its benchmarked chunks.">
            <div className="divide-y divide-line">
              <Field label="Chunk size, in tokens" hint={`${ranges?.chunk_size?.join(' to ')}. The embedding model cuts text off at 256.`}>
                <input type="number" className={fieldClass} value={form.chunk_size} onChange={(event) => update({ chunk_size: Number(event.target.value) })} />
              </Field>
              <Field label="Overlap, in tokens" hint={`${ranges?.chunk_overlap?.join(' to ')}, and smaller than the chunk size.`}>
                <input type="number" className={fieldClass} value={form.chunk_overlap} onChange={(event) => update({ chunk_overlap: Number(event.target.value) })} />
              </Field>
            </div>
          </Section>

          <div className="mt-4 flex flex-wrap items-center gap-3">
            <Button variant="primary" disabled={save.isPending} onClick={() => save.mutate(form)}>Save settings</Button>
            {saved && <span role="status" className="text-good">Settings saved.</span>}
          </div>
          {save.isError && <div className="mt-3"><ErrorNotice error={save.error} /></div>}

          <Section title="Server configuration" description="Read-only. Change these in the server environment.">
            <TableWrap>
              <tbody>
                <tr><th scope="row" className="w-52">Generation model</th><td className="num">{config.data.generation_model}</td></tr>
                <tr><th scope="row">Reranker</th><td className="num">{config.data.reranker_model}</td></tr>
                <tr><th scope="row">Embedding model</th><td className="num">{config.data.embedding_model}</td></tr>
                <tr><th scope="row">NVIDIA key</th><td><Badge tone={config.data.security.provider_configured ? 'good' : 'bad'}>{config.data.security.provider_configured ? 'Configured' : 'Missing'}</Badge></td></tr>
                <tr><th scope="row">Access token required</th><td>{config.data.security.api_token_required ? 'Yes' : 'No. Keep this server local.'}</td></tr>
                <tr><th scope="row">Streaming</th><td>Not supported. Answers appear after validation finishes.</td></tr>
              </tbody>
            </TableWrap>
          </Section>
        </>
      )}
    </Page>
  )
}
