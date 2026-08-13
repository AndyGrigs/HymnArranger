import { useCallback, useEffect, useRef, useState } from 'react'
import { api, ApiError } from '../api'
import type { AnalyzeOut, ScoreSource } from '../api'

interface State {
  source: ScoreSource | null
  fileName: string | null
  analysis: AnalyzeOut | null
  loading: boolean
  error: string | null
}

const EMPTY: State = {
  source: null,
  fileName: null,
  analysis: null,
  loading: false,
  error: null,
}

/**
 * Тримає обране джерело нот і результат /analyze.
 * Кожне нове завантаження скасовує попередній запит — інакше повільна
 * відповідь на старий файл може перекрити свіжу.
 */
export function useAnalysis() {
  const [state, setState] = useState<State>(EMPTY)
  const abortRef = useRef<AbortController | null>(null)

  const load = useCallback(async (source: ScoreSource, fileName: string) => {
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller

    setState({ source, fileName, analysis: null, loading: true, error: null })

    try {
      const analysis = await api.analyze(source, null, controller.signal)
      if (controller.signal.aborted) return
      setState({ source, fileName, analysis, loading: false, error: null })
    } catch (err) {
      if (controller.signal.aborted) return
      const message =
        err instanceof ApiError
          ? err.message
          : 'Не вдалося зв’язатися з сервером. Перевір, чи запущено бекенд.'
      setState({ source, fileName, analysis: null, loading: false, error: message })
    }
  }, [])

  const reset = useCallback(() => {
    abortRef.current?.abort()
    setState(EMPTY)
  }, [])

  useEffect(() => () => abortRef.current?.abort(), [])

  return { ...state, load, reset }
}