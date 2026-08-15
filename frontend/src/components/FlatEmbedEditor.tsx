import { useEffect, useRef, useState } from 'react'
import Embed from 'flat-embed'

const FLAT_APP_ID = import.meta.env.VITE_FLAT_APP_ID

/**
 * УВАГА: це шорткати Flat, а не MuseScore.
 * У Flat 1 — це ціла, і далі за спаданням; режиму «введення нот» (N) немає взагалі:
 * ставиш курсор кліком у такт і одразу друкуєш A–G.
 */
const DURATIONS = [
  { key: '1', label: 'ціла' },
  { key: '2', label: 'половинна' },
  { key: '3', label: 'чвертка' },
  { key: '4', label: '8-ма' },
  { key: '5', label: '16-та' },
  { key: '6', label: '32-га' },
]

interface FlatEmbedEditorProps {
  musicXml?: string
  scoreId?: string
  /** Викликається з інстансом, коли редактор готовий, і з null — коли зникає. */
  onEmbedChange?: (embed: Embed | null) => void
  height?: string
}

export function FlatEmbedEditor({
  musicXml,
  scoreId,
  onEmbedChange,
  height = '600px',
}: FlatEmbedEditorProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const embedRef = useRef<Embed | null>(null)
  const [isReady, setIsReady] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // onEmbedChange тримаємо в ref, щоб інлайнова стрілка з App не була в deps.
  const notifyRef = useRef(onEmbedChange)
  notifyRef.current = onEmbedChange

  useEffect(() => {
    const host = containerRef.current
    if (!host) return

    if (!FLAT_APP_ID) {
      setError(
        'VITE_FLAT_APP_ID не заданий. Без App ID редагування працює лише на localhost — ' +
          'і саме на localhost, а не на 127.0.0.1 чи IP у мережі.',
      )
    }

    let cancelled = false

    // Ключі з undefined flat-embed серіалізує в URL як "appId=undefined",
    // тому додаємо appId лише коли він реально є.
    const embedParams: Record<string, string> = {
      controlsPosition: 'bottom',
      mode: 'edit',
    }
    if (FLAT_APP_ID) embedParams.appId = FLAT_APP_ID

    const embed = new Embed(host, { score: scoreId, embedParams })
    embedRef.current = embed

    embed.on('restrictedFeatureAttempt', (...info: unknown[]) => {
      console.warn('[flat-embed] дію заблоковано:', ...info)
      setError(
        'Редагування заблоковане. Перевір, що домен, з якого відкрито сторінку, ' +
          'є в whitelist твого App ID у Flat (Embed → Settings).',
      )
    })

    embed
      .ready()
      .then(async () => {
        if (cancelled) return
        if (musicXml) await embed.loadMusicXML(musicXml)
        if (cancelled) return
        setIsReady(true)
        embed.focusScore().catch(() => {})
        notifyRef.current?.(embed)
      })
      .catch((err) => {
        if (cancelled) return
        console.error('[flat-embed]', err)
        setError('Не вдалося завантажити редактор Flat.')
      })

    return () => {
      cancelled = true
      embedRef.current = null
      // Головне: прибрати iframe. Інакше flat-embed при наступному
      // `new Embed(host, ...)` знайде старий iframe у контейнері, поверне
      // старий інстанс і мовчки проігнорує нові embedParams.
      host.querySelector('iframe')?.remove()
      // І сказати батьку, що поточний ref більше не валідний — інакше
      // getMusicXML() на відʼєднаному iframe зависне назавжди.
      notifyRef.current?.(null)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function handleFocus() {
    embedRef.current?.focusScore().catch(() => {})
  }

  return (
    <div className="space-y-2">
      {/* Підказка по клавіатурі — за реальними шорткатами Flat */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 rounded-lg border border-ink/10 bg-white px-3 py-2 text-xs text-ink/70">
        <span className="font-semibold text-ink/50 uppercase tracking-wide">Як набирати ноти</span>

        <span className="flex items-center gap-1">
          <span className="text-muted">Крок 1 — клікни в такт, щоб зʼявився курсор</span>
        </span>

        <span className="flex items-center gap-1.5">
          <span className="text-muted">Крок 2 — тривалість</span>
          {DURATIONS.map(({ key, label }) => (
            <span key={key} className="flex items-center gap-0.5">
              <kbd className="rounded border border-ink/20 bg-ink/5 px-1 font-mono">{key}</kbd>
              <span className="text-ink/40">{label}</span>
            </span>
          ))}
        </span>

        <span className="flex items-center gap-1">
          <span className="text-muted">Крок 3 — назва ноти</span>
          <span className="font-mono font-bold tracking-widest text-accent">A B C D E F G</span>
        </span>

        <span className="flex items-center gap-1">
          <span className="text-muted">Повний список —</span>
          <kbd className="rounded border border-ink/20 bg-ink/5 px-1 font-mono">Alt</kbd>
          <span className="text-ink/40">+</span>
          <kbd className="rounded border border-ink/20 bg-ink/5 px-1 font-mono">/</kbd>
        </span>

        <button
          type="button"
          onClick={handleFocus}
          disabled={!isReady}
          className="ml-auto rounded border border-ink/15 bg-ink/5 px-2 py-1 font-medium text-ink/60 transition hover:bg-ink/10 disabled:opacity-40"
        >
          Повернути фокус у редактор
        </button>
      </div>

      {error && (
        <div className="flex items-start gap-2 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-800">
          <span>⚠</span>
          <span className="flex-1">{error}</span>
          <button
            type="button"
            className="text-amber-500 hover:text-amber-700"
            onClick={() => setError(null)}
          >
            ✕
          </button>
        </div>
      )}

      <div ref={containerRef} style={{ width: '100%', height }} />
      {!isReady && <p className="text-center text-sm text-muted">Завантаження редактора…</p>}
    </div>
  )
}