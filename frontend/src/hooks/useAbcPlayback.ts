import { useCallback, useEffect, useRef, useState } from 'react'
import abcjs from 'abcjs'
import { useTranslation } from 'react-i18next'

// General MIDI program 21 (0-indexed) = Accordion, як у згенерованих партитурах.
const GM_ACCORDION_PROGRAM = 21
// Клас, який CSS фарбує в синій (див. index.css).
const PLAYING_CLASS = 'ha-note-playing'

export type PlayState = 'idle' | 'loading' | 'playing' | 'paused'

/**
 * Відтворення відрендереної abcjs-партитури з підсвічуванням нот, що звучать.
 *
 * @param getVisual  повертає TuneObject, який зараз намальований на екрані
 *                   (саме його елементи abcjs підсвічує під час гри)
 * @param resetKey   змінюється разом з нотами — відтворення тоді зупиняється,
 *                   бо старий звук більше не відповідає тому, що на екрані
 */
export function useAbcPlayback(
  getVisual: () => abcjs.TuneObject | null | undefined,
  resetKey: unknown,
) {
  const { t } = useTranslation()
  const [playState, setPlayState] = useState<PlayState>('idle')

  const synthRef = useRef<abcjs.SynthObjectController | null>(null)
  // Чи завантажено поточну мелодію в синтезатор (після «Стоп» — ні, граємо з початку).
  const tuneReadyRef = useRef(false)
  const lastLineRef = useRef<number | null>(null)
  const highlightedRef = useRef<HTMLElement[]>([])
  const getVisualRef = useRef(getVisual)
  getVisualRef.current = getVisual

  const clearHighlight = useCallback(() => {
    highlightedRef.current.forEach((el) => el.classList.remove(PLAYING_CLASS))
    highlightedRef.current = []
    lastLineRef.current = null
  }, [])

  const stop = useCallback(() => {
    synthRef.current?.pause()
    tuneReadyRef.current = false
    clearHighlight()
    setPlayState('idle')
  }, [clearHighlight])

  useEffect(() => {
    stop()
  }, [resetKey, stop])

  useEffect(() => () => {
    synthRef.current?.pause()
  }, [])

  const pause = useCallback(() => {
    synthRef.current?.pause()
    setPlayState('paused')
  }, [])

  const play = useCallback(async () => {
    if (playState === 'loading' || playState === 'playing') return
    if (playState === 'paused' && synthRef.current) {
      synthRef.current.play()
      setPlayState('playing')
      return
    }

    const visual = getVisualRef.current()
    if (!visual) return

    if (!abcjs.synth.supportsAudio()) {
      alert(t('panels.player.noAudio'))
      return
    }

    setPlayState('loading')
    try {
      if (!synthRef.current) {
        const controller = new abcjs.synth.SynthController()
        // Власний інтерфейс контролера не потрібен — він малюється у відчепленому
        // елементі, а керуємо ми власними кнопками.
        controller.load(
          document.createElement('div'),
          {
            onEvent: (ev) => {
              clearHighlight()
              if (!ev?.elements) return
              const els = ev.elements.flat()
              els.forEach((el) => el.classList.add(PLAYING_CLASS))
              highlightedRef.current = els

              // На новому рядку нот підтягуємо сторінку, щоб звучання лишалось у полі зору.
              if (ev.line !== undefined && ev.line !== lastLineRef.current) {
                lastLineRef.current = ev.line
                els[0]?.scrollIntoView?.({ block: 'nearest', behavior: 'smooth' })
              }
            },
            onFinished: () => {
              clearHighlight()
              tuneReadyRef.current = false
              setPlayState('idle')
            },
          },
          {
            displayLoop: false,
            displayRestart: false,
            displayPlay: false,
            displayProgress: false,
            displayWarp: false,
          },
        )
        synthRef.current = controller
      }
      if (!tuneReadyRef.current) {
        await synthRef.current.setTune(visual, false, {
          program: GM_ACCORDION_PROGRAM,
          // Ліва рука вже виписана нотами — автоакомпанемент по акордах не потрібен.
          chordsOff: true,
        })
        tuneReadyRef.current = true
      }
      synthRef.current.play()
      setPlayState('playing')
    } catch {
      tuneReadyRef.current = false
      setPlayState('idle')
    }
  }, [playState, clearHighlight, t])

  return { playState, play, pause, stop }
}
