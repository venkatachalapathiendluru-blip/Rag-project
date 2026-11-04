import { AlertCircle, RefreshCw } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { ReactNode } from 'react'
import { ApiFailure, toApiFailure } from '@/services/api'
import { Button } from './ui/button'

export function Skeleton({ rows = 4 }: { rows?: number }) {
  return (
    <div className="space-y-2" role="status" aria-label="Loading">
      {Array.from({ length: rows }, (_, index) => (
        <div key={index} className="h-9 animate-pulse rounded bg-panel" />
      ))}
    </div>
  )
}

export function ErrorNotice({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const failure: ApiFailure = toApiFailure(error)
  return (
    <div role="alert" className="flex flex-wrap items-start gap-3 rounded-md bg-bad-soft p-3 text-sm text-bad">
      <AlertCircle className="mt-0.5 size-4 shrink-0" />
      <div className="min-w-0 flex-1">
        <p className="font-medium">{failure.message}</p>
        {failure.status === 401 && (
          <p className="mt-1">Add the access token in <Link className="underline" to="/settings">Settings</Link>.</p>
        )}
        {failure.requestId && <p className="num mt-1 text-xs opacity-80">Request {failure.requestId}</p>}
      </div>
      {onRetry && (
        <Button size="sm" onClick={onRetry}><RefreshCw /> Try again</Button>
      )}
    </div>
  )
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="rounded-md border border-dashed border-line-strong px-5 py-8 text-center">
      <p className="font-medium">{title}</p>
      {children && <div className="mx-auto mt-1 max-w-prose text-sm text-ink-2">{children}</div>}
    </div>
  )
}

export function PageHeader({ title, description, actions }: { title: string; description?: string; actions?: ReactNode }) {
  return (
    <header className="mb-6 flex flex-wrap items-start justify-between gap-3">
      <div className="min-w-0">
        <h1>{title}</h1>
        {description && <p className="mt-1 max-w-[70ch] text-ink-2">{description}</p>}
      </div>
      {actions}
    </header>
  )
}

export function Section({ title, description, aside, children }: { title: string; description?: string; aside?: ReactNode; children: ReactNode }) {
  return (
    <section className="mt-8 first:mt-0">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2>{title}</h2>
          {description && <p className="mt-0.5 max-w-[75ch] text-[13px] text-ink-2">{description}</p>}
        </div>
        {aside}
      </div>
      {children}
    </section>
  )
}

export function TableWrap({ children }: { children: ReactNode }) {
  return <div className="relative overflow-x-auto rounded-md border border-line"><table className="w-full border-collapse text-left text-[13px] [&_td]:border-t [&_td]:border-line [&_td]:px-3 [&_td]:py-2 [&_th]:bg-panel [&_th]:px-3 [&_th]:py-2 [&_th]:font-medium [&_th]:whitespace-nowrap [&_th]:text-ink-2">{children}</table></div>
}

export function StatStrip({ items }: { items: { label: string; value: ReactNode }[] }) {
  return (
    <dl className="grid grid-cols-2 overflow-hidden rounded-md border border-line sm:grid-cols-[repeat(auto-fit,minmax(8rem,1fr))]">
      {items.map((item) => (
        <div key={item.label} className="border-b border-r border-line px-4 py-3 last:border-r-0 sm:border-b-0">
          <dt className="text-[13px] text-ink-2">{item.label}</dt>
          <dd className="num mt-0.5 text-lg font-medium">{item.value}</dd>
        </div>
      ))}
    </dl>
  )
}
