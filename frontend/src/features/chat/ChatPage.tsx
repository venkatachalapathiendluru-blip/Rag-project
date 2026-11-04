import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Check, Copy, Plus, Send } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { EmptyState, ErrorNotice, Skeleton } from '@/components/states'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { api } from '@/services/api'
import type { Citation, Message } from '@/types/api'
import { AnswerMarkdown } from './AnswerMarkdown'
import { EvidencePanel } from './EvidencePanel'
import { ValidationStrip } from './ValidationStrip'

const selectClass = 'h-8 max-w-44 rounded-md border border-line-strong bg-raised px-2 text-[13px] text-ink'

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  return (
    <Button
      variant="ghost"
      size="sm"
      aria-label="Copy response"
      onClick={async () => {
        await navigator.clipboard.writeText(text)
        setCopied(true)
        setTimeout(() => setCopied(false), 1500)
      }}
    >
      {copied ? <Check /> : <Copy />} {copied ? 'Copied' : 'Copy'}
    </Button>
  )
}

function Elapsed() {
  const [seconds, setSeconds] = useState(0)
  useEffect(() => {
    const timer = setInterval(() => setSeconds((value) => value + 1), 1000)
    return () => clearInterval(timer)
  }, [])
  return <span className="num">{seconds}s</span>
}

export function ChatPage() {
  const params = useParams()
  const conversationId = params.conversationId ? Number(params.conversationId) : undefined
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [draft, setDraft] = useState('')
  const [selected, setSelected] = useState<Citation | null>(null)
  const [profileId, setProfileId] = useState('')
  const [documentId, setDocumentId] = useState('')
  const endRef = useRef<HTMLDivElement>(null)

  const config = useQuery({ queryKey: ['config'], queryFn: api.config })
  const documents = useQuery({ queryKey: ['documents'], queryFn: api.documents })
  const conversations = useQuery({ queryKey: ['conversations'], queryFn: api.conversations })
  const conversation = useQuery({
    queryKey: ['conversation', conversationId],
    queryFn: () => api.conversation(conversationId!),
    enabled: conversationId !== undefined,
  })

  const send = useMutation({
    mutationFn: (question: string) => api.chat({
      question,
      conversation_id: conversationId,
      profile_id: profileId || undefined,
      document_ids: documentId ? [Number(documentId)] : undefined,
    }),
    onSuccess: async (result) => {
      setDraft('')
      await queryClient.invalidateQueries({ queryKey: ['conversation', result.conversation_id] })
      await queryClient.invalidateQueries({ queryKey: ['conversations'] })
      if (result.conversation_id !== conversationId) navigate(`/chat/${result.conversation_id}`)
    },
  })

  useEffect(() => {
    setSelected(null)
    send.reset()
    // Changing conversation clears the panel. send is stable enough for this purpose.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversationId])

  const messages: Message[] = conversation.data?.messages ?? []

  useEffect(() => {
    endRef.current?.scrollIntoView?.({ block: 'end' })
  }, [messages.length, send.isPending])

  const submit = () => {
    const question = draft.trim()
    if (question && !send.isPending) send.mutate(question)
  }

  const readyDocuments = documents.data?.filter((item) => item.status === 'ready') ?? []
  const noDocuments = documents.isSuccess && readyDocuments.length === 0

  return (
    <div className="flex h-full min-h-0">
      <div className="hidden w-60 shrink-0 flex-col border-r border-line md:flex">
        <div className="p-3">
          <Button className="w-full" asChild><Link to="/chat"><Plus /> New conversation</Link></Button>
        </div>
        <nav aria-label="Conversations" className="min-h-0 flex-1 space-y-0.5 overflow-y-auto px-2 pb-3">
          {conversations.data?.map((item) => (
            <Link
              key={item.id}
              to={`/chat/${item.id}`}
              className={cn(
                'block truncate rounded-md px-2.5 py-1.5 text-[13px] transition-colors duration-150',
                item.id === conversationId ? 'bg-accent-soft font-medium text-accent' : 'text-ink-2 hover:bg-panel hover:text-ink',
              )}
              title={item.title}
            >
              {item.title}
            </Link>
          ))}
        </nav>
      </div>

      <div className="flex min-w-0 flex-1 flex-col">
        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-6 sm:px-6">
          <div className="mx-auto max-w-3xl space-y-6">
            {conversation.isLoading && <Skeleton rows={3} />}
            {conversation.isError && <ErrorNotice error={conversation.error} onRetry={() => conversation.refetch()} />}
            {conversationId === undefined && !send.isPending && (
              noDocuments
                ? <EmptyState title="Nothing is indexed yet">Upload a document in <Link className="text-accent underline" to="/documents">Documents</Link>, then ask about it here.</EmptyState>
                : <EmptyState title="Ask about your indexed documents">Answers cite their source chunks. Select a citation to read the exact text behind it.</EmptyState>
            )}
            {messages.map((message) => (
              message.role === 'user' ? (
                <div key={message.id} className="ml-auto w-fit max-w-[85%] whitespace-pre-wrap break-words rounded-lg bg-accent-soft px-3.5 py-2">{message.content}</div>
              ) : (
                <article key={message.id} aria-label="Assistant answer">
                  <AnswerMarkdown
                    content={message.content}
                    citations={message.citations ?? []}
                    selected={selected?.chunk_id ?? null}
                    onSelect={setSelected}
                  />
                  <ValidationStrip status={message.status} validation={message.validation} />
                  <div className="mt-1 -ml-2"><CopyButton text={message.content} /></div>
                </article>
              )
            ))}
            {send.isPending && (
              <>
                <div className="ml-auto w-fit max-w-[85%] whitespace-pre-wrap break-words rounded-lg bg-accent-soft px-3.5 py-2">{send.variables}</div>
                <p role="status" className="animate-pulse text-ink-2">Retrieving evidence and writing the answer. <Elapsed /></p>
              </>
            )}
            {send.isError && <ErrorNotice error={send.error} onRetry={() => send.mutate(send.variables!)} />}
            <div ref={endRef} />
          </div>
        </div>

        <form
          className="shrink-0 border-t border-line p-3 sm:px-6"
          onSubmit={(event) => { event.preventDefault(); submit() }}
        >
          <div className="mx-auto max-w-3xl">
            <div className="flex items-end gap-2">
              <textarea
                aria-label="Your question"
                value={draft}
                maxLength={2000}
                rows={2}
                placeholder="Ask a question about your documents"
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); submit() }
                }}
                className="min-h-14 flex-1 resize-none rounded-md border border-line-strong bg-raised px-3 py-2 placeholder:text-ink-3"
              />
              <Button type="submit" variant="primary" disabled={!draft.trim() || send.isPending}><Send /> Ask</Button>
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-2 text-[13px] text-ink-2">
              <label className="flex items-center gap-1.5">
                Retrieval
                <select className={selectClass} value={profileId} onChange={(event) => setProfileId(event.target.value)}>
                  <option value="">Default</option>
                  {config.data?.profiles.map((profile) => <option key={profile.id} value={profile.id}>{profile.label}</option>)}
                </select>
              </label>
              <label className="flex items-center gap-1.5">
                Search in
                <select className={selectClass} value={documentId} onChange={(event) => setDocumentId(event.target.value)}>
                  <option value="">All documents</option>
                  {readyDocuments.map((item) => <option key={item.id} value={item.id}>{item.filename}</option>)}
                </select>
              </label>
            </div>
          </div>
        </form>
      </div>

      {selected && <EvidencePanel citation={selected} onClose={() => setSelected(null)} />}
    </div>
  )
}
