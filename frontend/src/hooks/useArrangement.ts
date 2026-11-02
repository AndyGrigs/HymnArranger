import { useCallback, useEffect, useRef, useState } from 'react'
import { api, ApiError } from '../api'
import type { ScoreSource } from '../api'
import { useAuth } from './useAuth'
import i18n from '../i18n'

export type Mode = 'suite' | 'preset' | 'merge' | 'mix' | 'style'

/** Рядок у списку розділів під нотами. */
export interface SectionRow {
  label: string
  detail: string
}

export interface Arrangement {
  musicxml: string
  /** ABC-нотація для відображення через abcjs (може бути відсутня при помилці конвертації). */
  abc?: string
  title: string
  mode: Mode
  sections: SectionRow[]
  /** Параметри, якими це згенеровано — потрібні для /midi і завантаження. */
  params: Record<string, unknown>
}

interface Options {
  preset?: string
  seed?: number | null
  varyBass?: boolean
  strophes?: number
  coda?: boolean
  /** Пресети міксу в порядку чергування. */
  mixPresets?: string[]
  barsPerPhrase?: number
}

export function useArrangement() {
  const { token } = useAuth()
  const [result, setResult] = useState<Arrangement | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const tokenRef = useRef(token)
  tokenRef.current = token

  const generate = useCallback(
    async (source: ScoreSource, mode: Mode, opts: Options = {}) => {
      abortRef.current?.abort()
      const controller = new AbortController()
      abortRef.current = controller
      const tok = tokenRef.current ?? undefined

      setLoading(true)
      setError(null)

      try {
        let next: Arrangement

        if (mode === 'suite') {
          const params = { seed: opts.seed ?? null, vary_bass: opts.varyBass ?? true }
          const data = await api.suite(source, params, controller.signal, tok)
          next = {
            musicxml: data.musicxml,
            abc: data.abc,
            title: i18n.t('panels.arrangement.suiteTitle'),
            mode,
            params,
            sections: data.sections.map((s) => ({
              label: `${s.index}. ${s.name}`,
              detail: i18n.t('panels.arrangement.tempoBass', { tempo: s.tempo, bass: s.bass }),
            })),
          }
        } else if (mode === 'preset') {
          const preset = opts.preset!
          const data = await api.arrange(source, preset, controller.signal, tok)
          next = {
            musicxml: data.musicxml,
            abc: data.abc,
            title: data.name,
            mode,
            params: { preset },
            sections: [{ label: data.name, detail: i18n.t('panels.arrangement.tempo', { tempo: data.tempo }) }],
          }
        } else if (mode === 'mix') {
          const params = {
            presets: (opts.mixPresets ?? []).join(','),
            bars_per_phrase: opts.barsPerPhrase ?? 4,
          }
          const data = await api.mix(source, params, controller.signal, tok)
          next = {
            musicxml: data.musicxml,
            abc: data.abc,
            title: i18n.t('panels.arrangement.mixTitle'),
            mode,
            params,
            sections: data.sections.map((s) => ({
              label: `${s.index}. ${s.name}`,
              detail: i18n.t('panels.arrangement.mixBars', { from: s.from_bar, to: s.to_bar }),
            })),
          }
        } else if (mode === 'style') {
          const params = {
            style: 'sakala',
            strophes: opts.strophes ?? 5,
            coda: opts.coda ?? true,
          }
          const data = await api.style(source, params, controller.signal, tok)
          next = {
            musicxml: data.musicxml,
            abc: data.abc,
            title: i18n.t('panels.arrangement.styleTitle', { key: data.key, meter: data.meter }),
            mode,
            params,
            sections: data.sections.map((s) => ({
              label: `${s.index}. ${s.name}`,
              detail: s.octave ? i18n.t('panels.arrangement.octaveUp') : '',
            })),
          }
        } else {
          const data = await api.merge(source, controller.signal, tok)
          next = {
            musicxml: data.musicxml,
            abc: data.abc,
            title: i18n.t('panels.arrangement.mergeTitle'),
            mode,
            params: {},
            sections: data.sections.map((s) => ({
              label: s.name,
              detail: s.preset,
            })),
          }
        }

        if (controller.signal.aborted) return
        setResult(next)
      } catch (err) {
        if (controller.signal.aborted) return
        setError(
          err instanceof ApiError
            ? err.message
            : i18n.t('panels.arrangement.failed'),
        )
      } finally {
        if (!controller.signal.aborted) setLoading(false)
      }
    },
    [],
  )

  const clear = useCallback(() => {
    abortRef.current?.abort()
    setResult(null)
    setError(null)
    setLoading(false)
  }, [])

  /** Підмінює musicxml у поточному результаті — напр. після ручного редагування. */
  const updateMusicXml = useCallback((musicxml: string) => {
    setResult((prev) => (prev ? { ...prev, musicxml } : prev))
  }, [])

  useEffect(() => () => abortRef.current?.abort(), [])

  return { result, loading, error, generate, clear, updateMusicXml }
}