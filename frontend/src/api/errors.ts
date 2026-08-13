/**
 * FastAPI віддає помилки як {"detail": "..."} — або як масив об'єктів
 * при помилці валідації. Зводимо обидва випадки до одного рядка,
 * щоб компонент показував повідомлення, а не [object Object].
 */
export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

interface ValidationItem {
  loc?: (string | number)[]
  msg?: string
}

export function extractDetail(payload: unknown, status: number): string {
  if (typeof payload === 'string' && payload.trim()) return payload

  if (payload && typeof payload === 'object' && 'detail' in payload) {
    const detail = (payload as { detail: unknown }).detail

    if (typeof detail === 'string') return detail

    if (Array.isArray(detail)) {
      const parts = (detail as ValidationItem[])
        .map((item) => {
          const where = item.loc?.slice(1).join('.') ?? ''
          return where ? `${where}: ${item.msg ?? ''}` : (item.msg ?? '')
        })
        .filter(Boolean)
      if (parts.length) return parts.join('; ')
    }
  }

  return `Сервер повернув помилку ${status}`
}