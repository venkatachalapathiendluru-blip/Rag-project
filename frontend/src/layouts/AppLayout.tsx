import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import {
  Activity, BarChart3, FileText, FlaskConical, LayoutDashboard, Menu, MessageSquare, MessagesSquare, Settings, X,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

const NAV = [
  { to: '/', label: 'Overview', icon: LayoutDashboard },
  { to: '/chat', label: 'AI Chat', icon: MessageSquare },
  { to: '/documents', label: 'Documents', icon: FileText },
  { to: '/conversations', label: 'Conversations', icon: MessagesSquare },
  { to: '/evaluation', label: 'Evaluation', icon: BarChart3 },
  { to: '/experiments', label: 'Retrieval Experiments', icon: FlaskConical },
  { to: '/monitoring', label: 'System Monitoring', icon: Activity },
  { to: '/settings', label: 'Settings', icon: Settings },
]

export function AppLayout() {
  const [open, setOpen] = useState(false)
  return (
    <div className="flex h-full min-h-0">
      {open && <button aria-label="Close menu" className="fixed inset-0 z-30 bg-black/40 lg:hidden" onClick={() => setOpen(false)} />}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-40 flex w-60 shrink-0 flex-col border-r border-line bg-panel transition-transform duration-200 lg:static lg:translate-x-0',
          open ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="flex h-14 items-center justify-between px-4">
          <span className="font-semibold tracking-tight">Enterprise RAG</span>
          <Button variant="ghost" size="icon" className="lg:hidden" aria-label="Close menu" onClick={() => setOpen(false)}><X /></Button>
        </div>
        <nav aria-label="Main" className="flex-1 space-y-0.5 overflow-y-auto px-2 pb-4">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              onClick={() => setOpen(false)}
              className={({ isActive }) => cn(
                'flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm transition-colors duration-150 [&_svg]:size-4',
                isActive ? 'bg-accent-soft font-medium text-accent' : 'text-ink-2 hover:bg-line/50 hover:text-ink',
              )}
            >
              <Icon /> {label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex h-12 shrink-0 items-center gap-2 border-b border-line px-3 lg:hidden">
          <Button variant="ghost" size="icon" aria-label="Open menu" onClick={() => setOpen(true)}><Menu /></Button>
          <span className="font-semibold tracking-tight">Enterprise RAG</span>
        </div>
        <main className="min-h-0 flex-1 overflow-y-auto"><Outlet /></main>
      </div>
    </div>
  )
}

export function Page({ children }: { children: React.ReactNode }) {
  return <div className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 lg:px-8">{children}</div>
}
