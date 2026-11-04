import { Navigate, Route, Routes } from 'react-router-dom'
import { ChatPage } from '@/features/chat/ChatPage'
import { ConversationsPage } from '@/features/conversations/ConversationsPage'
import { DocumentsPage } from '@/features/documents/DocumentsPage'
import { EvaluationPage } from '@/features/evaluation/EvaluationPage'
import { ExperimentsPage } from '@/features/experiments/ExperimentsPage'
import { MonitoringPage } from '@/features/monitoring/MonitoringPage'
import { OverviewPage } from '@/features/overview/OverviewPage'
import { SettingsPage } from '@/features/settings/SettingsPage'
import { AppLayout } from '@/layouts/AppLayout'

export function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<OverviewPage />} />
        <Route path="chat" element={<ChatPage />} />
        <Route path="chat/:conversationId" element={<ChatPage />} />
        <Route path="documents" element={<DocumentsPage />} />
        <Route path="conversations" element={<ConversationsPage />} />
        <Route path="evaluation" element={<EvaluationPage />} />
        <Route path="experiments" element={<ExperimentsPage />} />
        <Route path="monitoring" element={<MonitoringPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
