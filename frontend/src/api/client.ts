import { ApiError, extractDetail } from './errors'
import type {
  AnalyzeOut,
  ArrangeOut,
  AuthToken,
  HealthOut,
  MergeOut,
  MessageOut,
  ScoreSource,
  StyleOut,
  StyleParams,
  SuiteOut,
  SuiteParams,
  User,
  WorkDetail,
  WorkSummary,
} from './types'

const BASE = import.meta.env.VITE_API_BASE ?? '/api'

/**
 * Бекенд приймає ноти двома способами: multipart-файлом або JSON-тілом
 * з полем musicxml. Обираємо за типом джерела — решта коду про це не знає.
 */
function buildBody(source: ScoreSource): { body: BodyInit; headers?: HeadersInit } {
  if (source instanceof File) {
    const form = new FormData()
    form.append('file', source)
    // Content-Type не ставимо свідомо: браузер сам додасть boundary.
    return { body: form }
  }
  return {
    body: JSON.stringify({ musicxml: source.musicxml }),
    headers: { 'Content-Type': 'application/json' },
  }
}

/** Прибирає undefined і null, щоб у URL не летіло ?seed=undefined. */
function buildQuery(params: Record<string, unknown> = {}): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null) search.set(key, String(value))
  }
  const qs = search.toString()
  return qs ? `?${qs}` : ''
}

function authHeaders(token?: string): HeadersInit {
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function getJson<T>(path: string, token?: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${BASE}${path}`, { headers: authHeaders(token), signal })
  if (!response.ok) await failure(response)
  return (await response.json()) as T
}

async function sendJson<T>(
  method: 'POST' | 'DELETE',
  path: string,
  body?: unknown,
  token?: string,
  signal?: AbortSignal,
): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
    body: body !== undefined ? JSON.stringify(body) : undefined,
    signal,
  })
  if (!response.ok) await failure(response)
  return (await response.json()) as T
}

async function failure(response: Response): Promise<never> {
  let payload: unknown = null
  try {
    payload = await response.json()
  } catch {
    payload = await response.text().catch(() => null)
  }
  throw new ApiError(response.status, extractDetail(payload, response.status))
}

/** POST з нотами → JSON-відповідь. */
async function postJson<T>(
  path: string,
  source: ScoreSource,
  params?: Record<string, unknown>,
  signal?: AbortSignal,
  token?: string,
): Promise<T> {
  const { body, headers } = buildBody(source)
  const response = await fetch(`${BASE}${path}${buildQuery(params)}`, {
    method: 'POST',
    body,
    headers: { ...(headers as Record<string, string> | undefined), ...authHeaders(token) },
    signal,
  })
  if (!response.ok) await failure(response)
  return (await response.json()) as T
}

/** POST з нотами → бінарна відповідь (MIDI або файл на завантаження). */
async function postBlob(
  path: string,
  source: ScoreSource,
  params?: Record<string, unknown>,
  signal?: AbortSignal,
): Promise<Blob> {
  const { body, headers } = buildBody(source)
  const response = await fetch(`${BASE}${path}${buildQuery(params)}`, {
    method: 'POST',
    body,
    headers,
    signal,
  })
  if (!response.ok) await failure(response)
  return await response.blob()
}

export const api = {
  async health(signal?: AbortSignal): Promise<HealthOut> {
    const response = await fetch(`${BASE}/health`, { signal })
    if (!response.ok) await failure(response)
    return (await response.json()) as HealthOut
  },

  /** Метр, тональність, акорди, попередження, доступні пресети, план сюїти. */
  analyze(source: ScoreSource, seed?: number | null, signal?: AbortSignal) {
    return postJson<AnalyzeOut>('/analyze', source, { seed }, signal)
  },

  /** Одне аранжування обраним пресетом. */
  arrange(source: ScoreSource, preset: string, signal?: AbortSignal, token?: string) {
    return postJson<ArrangeOut>('/arrange', source, { preset }, signal, token)
  },

  /** Тема з варіаціями однією партитурою. */
  suite(source: ScoreSource, params: SuiteParams = {}, signal?: AbortSignal, token?: string) {
    return postJson<SuiteOut>('/suite', source, params, signal, token)
  },

  /** Усі доступні пресети підряд — для порівняння. */
  merge(source: ScoreSource, signal?: AbortSignal, token?: string) {
    return postJson<MergeOut>('/merge', source, undefined, signal, token)
  },

  /** Стильова обробка: строфи різної фактури, зв'язки, кода. */
  style(source: ScoreSource, params: StyleParams = {}, signal?: AbortSignal, token?: string) {
    return postJson<StyleOut>('/style', source, params, signal, token)
  },

  /** Конвертує будь-який формат партитури в ABC-нотацію. */
  convertToAbc(source: ScoreSource, signal?: AbortSignal) {
    return postJson<{ abc: string }>('/convert/abc', source, undefined, signal)
  },

  /** Конвертує передану партитуру MusicXML у MIDI без повторного аранжування. */
  midi(source: ScoreSource, signal?: AbortSignal) {
    return postBlob('/midi', source, { raw: true }, signal)
  },

  /**
   * Стискає переданий MusicXML у формат .mxl (ZIP) без повторного аранжування.
   * Завжди приймає вже готову партитуру з пам'яті — включно з ручними правками.
   */
  compress(source: ScoreSource, signal?: AbortSignal) {
    return postBlob('/compress', source, {}, signal)
  },

  // ── Авторизація ──────────────────────────────────────────────
  register(email: string, password: string, signal?: AbortSignal) {
    return sendJson<MessageOut>('POST', '/auth/register', { email, password }, undefined, signal)
  },

  login(email: string, password: string, signal?: AbortSignal) {
    return sendJson<AuthToken>('POST', '/auth/login', { email, password }, undefined, signal)
  },

  me(token: string, signal?: AbortSignal) {
    return getJson<User>('/auth/me', token, signal)
  },

  forgotPassword(email: string, signal?: AbortSignal) {
    return sendJson<MessageOut>('POST', '/auth/forgot-password', { email }, undefined, signal)
  },

  resetPassword(token: string, newPassword: string, signal?: AbortSignal) {
    return sendJson<MessageOut>(
      'POST', '/auth/reset-password', { token, new_password: newPassword }, undefined, signal,
    )
  },

  // ── Мої роботи ───────────────────────────────────────────────
  listWorks(token: string, signal?: AbortSignal) {
    return getJson<WorkSummary[]>('/works', token, signal)
  },

  getWork(token: string, workId: string, signal?: AbortSignal) {
    return getJson<WorkDetail>(`/works/${workId}`, token, signal)
  },

  deleteWork(token: string, workId: string, signal?: AbortSignal) {
    return sendJson<MessageOut>('DELETE', `/works/${workId}`, undefined, token, signal)
  },
}