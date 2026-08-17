import { ApiError, extractDetail } from './errors'
import type {
  AnalyzeOut,
  ArrangeOut,
  HealthOut,
  MergeOut,
  ScoreSource,
  SuiteOut,
  SuiteParams,
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
): Promise<T> {
  const { body, headers } = buildBody(source)
  const response = await fetch(`${BASE}${path}${buildQuery(params)}`, {
    method: 'POST',
    body,
    headers,
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
  arrange(source: ScoreSource, preset: string, signal?: AbortSignal) {
    return postJson<ArrangeOut>('/arrange', source, { preset }, signal)
  },

  /** Тема з варіаціями однією партитурою. */
  suite(source: ScoreSource, params: SuiteParams = {}, signal?: AbortSignal) {
    return postJson<SuiteOut>('/suite', source, params, signal)
  },

  /** Усі доступні пресети підряд — для порівняння. */
  merge(source: ScoreSource, signal?: AbortSignal) {
    return postJson<MergeOut>('/merge', source, undefined, signal)
  },

  /** Конвертує передану партитуру MusicXML у MIDI без повторного аранжування. */
  midi(source: ScoreSource, signal?: AbortSignal) {
    return postBlob('/midi', source, {}, signal)
  },

  /**
   * Стискає переданий MusicXML у формат .mxl (ZIP) без повторного аранжування.
   * Завжди приймає вже готову партитуру з пам'яті — включно з ручними правками.
   */
  compress(source: ScoreSource, signal?: AbortSignal) {
    return postBlob('/compress', source, {}, signal)
  },
}