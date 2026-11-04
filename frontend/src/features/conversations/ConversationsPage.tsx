import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, Trash2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import { EmptyState, ErrorNotice, PageHeader, Skeleton, TableWrap } from '@/components/states'
import { ConfirmDialog } from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'
import { Page } from '@/layouts/AppLayout'
import { dateTime } from '@/lib/format'
import { api } from '@/services/api'
import type { ConversationSummary } from '@/types/api'

function Row({ item }: { item: ConversationSummary }) {
  const queryClient = useQueryClient()
  const remove = useMutation({
    mutationFn: () => api.deleteConversation(item.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['conversations'] }),
  })
  return (
    <>
      <tr>
        <td className="max-w-md"><Link className="block truncate font-medium hover:text-accent" to={`/chat/${item.id}`}>{item.title}</Link></td>
        <td className="num">{item.message_count}</td>
        <td className="whitespace-nowrap">{dateTime(item.updated_at)}</td>
        <td className="text-right">
          <ConfirmDialog
            trigger={<Button size="icon" variant="ghost" aria-label={`Delete conversation ${item.title}`}><Trash2 /></Button>}
            title="Delete this conversation?"
            description="Its messages and saved evidence will be removed. This can't be undone."
            confirmLabel="Delete conversation"
            onConfirm={() => remove.mutate()}
          />
        </td>
      </tr>
      {remove.isError && <tr><td colSpan={4}><ErrorNotice error={remove.error} /></td></tr>}
    </>
  )
}

export function ConversationsPage() {
  const conversations = useQuery({ queryKey: ['conversations'], queryFn: api.conversations })
  return (
    <Page>
      <PageHeader
        title="Conversations"
        description="Saved chats, most recent first."
        actions={<Button variant="primary" asChild><Link to="/chat"><Plus /> New conversation</Link></Button>}
      />
      {conversations.isLoading && <Skeleton />}
      {conversations.isError && <ErrorNotice error={conversations.error} onRetry={() => conversations.refetch()} />}
      {conversations.data?.length === 0 && <EmptyState title="No conversations yet">Your first question in AI Chat starts one.</EmptyState>}
      {!!conversations.data?.length && (
        <TableWrap>
          <thead><tr><th>Title</th><th>Messages</th><th>Last activity</th><th><span className="sr-only">Actions</span></th></tr></thead>
          <tbody>{conversations.data.map((item) => <Row key={item.id} item={item} />)}</tbody>
        </TableWrap>
      )}
    </Page>
  )
}
