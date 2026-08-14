import { useEffect, useRef, useState } from 'react'
import { Volume2 } from 'lucide-react'
import { api, ApiError } from '../api'
import type { ScoreSource } from '../api'
import { Spinner } from './ui/Spinner'

// GM-банк від Magenta: єдиний публічний soundfont, у якому є
// програма 21 (акордеон). Без нього плеєр озвучить усе фортепіано.
const SOUNDFONT = 'https://storage.googleapis.com/magentadata/js/soundfonts/sgm_plus'

// Реєструємо <midi-player> ледащо — тільки після кліку користувача,
// щоб Tone.js не намагався відкрити AudioContext при завантаженні сторінки.
let midiPlayerRegistered = false
async function ensureMidiPlayer() {
  if (!midiPlayerRegistered) {
    await import('html-midi-player')
    midiPlayerRegistered = true
  }
}

interface Props {
  source: ScoreSource
  params: Record<string, unknown>
  /** Змінюється при кожній новій генерації — скидає завантажений звук. */
  resetKey: string
}

export function MidiPlayer({ source, params, resetKey }: Props) {
  const hostRef = useRef<HTMLDivElement>(null)
  const urlRef = useRef<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [ready, setReady] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function dispose() {
    if (urlRef.current) {
      URL.revokeObjectURL(urlRef.current)
      urlRef.current = null
    }
    if (hostRef.current) hostRef.current.innerHTML = ''
  }

  // Нова генерація — старий звук більше не відповідає нотам на екрані.
  useEffect(() => {
    dispose()
    setReady(false)
    setError(null)
    return dispose
  }, [resetKey])

  async function handleLoad() {
    setLoading(true)
    setError(null)

    try {
      await ensureMidiPlayer()
      const blob = await api.midi(source, params)
      dispose()

      const url = URL.createObjectURL(blob)
      urlRef.current = url

      // createElement замість JSX: web component не має типів React,
      // і в різних версіях React його довелося б описувати по-різному.
      const player = document.createElement('midi-player')
      player.setAttribute('sound-font', SOUNDFONT)
      player.setAttribute('src', url)
      player.style.width = '100%'

      hostRef.current?.appendChild(player)
      setReady(true)
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : 'Не вдалося отримати MIDI з сервера.',
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="rounded-lg border border-ink/10 bg-white p-4">
      {!ready && (
        <button
          type="button"
          onClick={handleLoad}
          disabled={loading}
          className="flex items-center gap-2 rounded border border-ink/15 px-4 py-2 text-sm transition hover:border-accent/40 disabled:opacity-50"
        >
          {loading ? <Spinner /> : <Volume2 className="h-4 w-4 text-accent" />}
          {loading ? 'Готую звук…' : 'Слухати'}
        </button>
      )}

      <div ref={hostRef} />

      {ready && (
        // Перший клік на play підвантажує ~2 МБ семплів, тому початок
        // відтворення помітно затримується — попереджаємо заздалегідь.
        <p className="mt-2 text-xs text-muted">
          Перший запуск завантажує банк звуків — можлива пауза в кілька секунд.
        </p>
      )}

      {error && <p className="mt-2 text-sm text-accent">{error}</p>}
    </div>
  )
}