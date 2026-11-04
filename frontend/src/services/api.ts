import axios, { AxiosError } from 'axios'
import type {
  AppConfig, ChatResponse, Comparison, Conversation, ConversationSummary, DocumentDetail,
  DocumentItem, Evaluation, EvaluationItem, Metrics, Overview, Settings,
} from '@/types/api'

const TOKEN_KEY = 'rag-api-token'

export function getToken() {
  try {
    return sessionStorage.getItem(TOKEN_KEY) ?? ''
  } catch {
    return ''
  }
}

export function setToken(value: string) {
  try {
    if (value) sessionStorage.setItem(TOKEN_KEY, value)
    else sessionStorage.removeItem(TOKEN_KEY)
  } catch {
    // Without storage the token cannot persist, and requests stay unauthenticated.
  }
}

export const http = axios.create({ baseURL: import.meta.env.VITE_API_BASE ?? '/api/v1', timeout: 300_000 })

http.interceptors.request.use((config) => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

export class ApiFailure extends Error {
  readonly code: string
  readonly status: number | null
  readonly requestId: string | null
  readonly details: unknown

  constructor(message: string, code: string, status: number | null, requestId: string | null, details: unknown) {
    super(message)
    this.code = code
    this.status = status
    this.requestId = requestId
    this.details = details
  }
}

export function toApiFailure(error: unknown): ApiFailure {
  if (error instanceof ApiFailure) return error
  const axiosError = error as AxiosError<{ error?: { code: string; message: string; request_id: string | null; details: unknown } }>
  const body = axiosError.response?.data?.error
  if (body) return new ApiFailure(body.message, body.code, axiosError.response?.status ?? null, body.request_id, body.details)
  if (axiosError.response) {
    return new ApiFailure(`The server responded with ${axiosError.response.status}.`, 'http_error', axiosError.response.status, null, null)
  }
  return new ApiFailure('The API could not be reached. Check that the backend is running.', 'network_error', null, null, null)
}

async function call<T>(request: Promise<{ data: T }>): Promise<T> {
  try {
    return (await request).data
  } catch (error) {
    throw toApiFailure(error)
  }
}

export const api = {
  config: () => call<AppConfig>(http.get('/config/')),
  overview: () => call<Overview>(http.get('/overview/')),
  metrics: () => call<Metrics>(http.get('/metrics/')),
  saveSettings: (changes: Partial<Settings>) => call<Settings>(http.put('/settings/', changes)),
  chat: (body: { question: string; conversation_id?: number; profile_id?: string; document_ids?: number[] }) =>
    call<ChatResponse>(http.post('/chat/', body)),
  conversations: () => call<ConversationSummary[]>(http.get('/conversations/')),
  conversation: (id: number) => call<Conversation>(http.get(`/conversations/${id}`)),
  deleteConversation: (id: number) => call<void>(http.delete(`/conversations/${id}`)),
  documents: () => call<DocumentItem[]>(http.get('/documents/')),
  document: (id: number) => call<DocumentDetail>(http.get(`/documents/${id}`)),
  deleteDocument: (id: number) => call<void>(http.delete(`/documents/${id}`)),
  reindex: (id: number) => call<{ document_id: number; job_id: number }>(http.post(`/documents/${id}/reindex/`)),
  upload: (file: File, onProgress: (percent: number) => void) => {
    const form = new FormData()
    form.append('file', file)
    return call<{ document_id: number; job_id: number }>(
      http.post('/documents/upload/', form, {
        onUploadProgress: (event) => {
          if (event.total) onProgress(Math.round((event.loaded / event.total) * 100))
        },
      }),
    )
  },
  evaluations: () => call<EvaluationItem[]>(http.get('/evaluations/')),
  evaluation: <S,>(id: string) => call<Evaluation<S>>(http.get(`/evaluations/${id}`)),
  comparison: () => call<Comparison>(http.get('/experiments/comparison/')),
}
