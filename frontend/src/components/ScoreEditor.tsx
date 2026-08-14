import { useEffect, useRef, useState } from 'react'
import Embed from 'flat-embed'
import { Check, RotateCcw } from 'lucide-react'
import { Spinner } from './ui/Spinner'
import { blankMusicXML, KEY_OPTIONS, METER_OPTIONS } from '../lib/blankScore'

const APP_ID = import.meta.env.VITE_FLAT_APP_ID as string | undefined

interface Props {
  /** Викликається з готовим MusicXML, коли користувач закінчив набір. */
  onSubmit: (musicxml: string) => void
  busy: boolean
}

export function ScoreEditor({ onSubmit, busy }: Props) {
  const hostRef = useRef<HTMLDivElement>(null)
  const embedRef = useRef<Embed | null>(null)

  const [meter, setMeter] = useState('4/4')
  const [fifths, setFifths] = useState(0)
  const [measures, setMeasures] = useState(16)
  const [started, setStarted] = useState(false)
  const [ready, setReady] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!started) return
    const host = hostRef.current
    if (!host) return

    let cancelled = false
    // StrictMode монтує ефект двічі — без очищення в контейнері
    // опиниться два iframe.
    host.innerHTML = ''
    setReady(false)
    setError(null)

    const embed = new Embed(host, {
      embedParams: {
        appId: APP_ID!,
        mode: 'edit',
        branding: false,
        controlsPosition: 'top',
      },
    })
    embedRef.current = embed

    embed
      .ready()
      // Партитуру не тримаємо на Flat — вантажимо згенерований шаблон
      // на льоту, тож акаунт із збереженими файлами не потрібен.
      .then(() => embed.loadMusicXML(blankMusicXML({ meter, fifths, measures })))
      .then(() => {
        if (!cancelled) setReady(true)
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setError(
          err instanceof Error
            ? `Редактор не запустився: ${err.message}`
            : 'Редактор не запустився.',
        )
      })

    return () => {
      cancelled = true
      embedRef.current = null
      host.innerHTML = ''
    }
  }, [started, meter, fifths, measures])

  async function handleSubmit() {
    const embed = embedRef.current
    if (!embed) return

    setExporting(true)
    setError(null)
    try {
      // Без compressed повертається саме рядок — рівно те, що чекає
      // поле musicxml у тілі запиту до бекенда.
      const xml = await embed.getMusicXML()
      if (typeof xml !== 'string') {
        throw new Error('Редактор повернув стиснений файл замість тексту')
      }
      onSubmit(xml)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Не вдалося забрати ноти з редактора.')
    } finally {
      setExporting(false)
    }
  }

  if (!APP_ID) {
    return (
      <div className="rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900">
        Редактор вимкнено: не заданий <code>VITE_FLAT_APP_ID</code>. Зареєструй
        застосунок на flat.io/developers/apps, впиши ідентифікатор у{' '}
        <code>.env</code> і перезапусти <code>npm run dev</code>.
      </div>
    )
  }

  if (!started) {
    return (
      <div className="rounded-lg border border-ink/10 bg-white p-5">
        <p className="text-sm text-muted">
          Задай розмір і тональність — редактор відкриється з готовою сіткою тактів.
        </p>

        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <label className="block">
            <span className="text-xs uppercase tracking-wide text-muted">Розмір</span>
            <select
              value={meter}
              onChange={(e) => setMeter(e.target.value)}
              className="mt-1.5 w-full rounded border border-ink/15 bg-white px-3 py-2 text-sm"
            >
              {METER_OPTIONS.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </label>

          <label className="block">
            <span className="text-xs uppercase tracking-wide text-muted">Тональність</span>
            <select
              value={fifths}
              onChange={(e) => setFifths(Number(e.target.value))}
              className="mt-1.5 w-full rounded border border-ink/15 bg-white px-3 py-2 text-sm"
            >
              {KEY_OPTIONS.map((k) => (
                <option key={k.fifths} value={k.fifths}>{k.label}</option>
              ))}
            </select>
          </label>

          <label className="block">
            <span className="text-xs uppercase tracking-wide text-muted">Тактів</span>
            <input
              type="number"
              min={4}
              max={64}
              value={measures}
              onChange={(e) => setMeasures(Math.min(64, Math.max(4, Number(e.target.value))))}
              className="mt-1.5 w-full rounded border border-ink/15 bg-white px-3 py-2 text-sm"
            />
          </label>
        </div>

        <button
          type="button"
          onClick={() => setStarted(true)}
          className="mt-4 rounded-lg bg-accent px-4 py-2.5 text-sm font-medium text-white transition hover:opacity-90"
        >
          Відкрити редактор
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <div className="relative overflow-hidden rounded-lg border border-ink/10 bg-white">
        {!ready && !error && (
          <div className="absolute inset-0 z-10 flex items-center justify-center gap-2 bg-white text-muted">
            <Spinner />
            <span className="text-sm">Завантажую редактор…</span>
          </div>
        )}
        <div ref={hostRef} style={{ height: 480 }} />
      </div>

      {error && (
        <p className="rounded border border-accent/30 bg-accent/5 px-4 py-2.5 text-sm text-accent">
          {error}
        </p>
      )}

      {/* Акорди потрібні для лівої руки — без них бекенд поверне
          попередження, а нижній нотоносець лишиться порожнім. */}
      <p className="text-xs text-muted">
        Не забудь проставити акордові символи над мелодією — з них будується
        партія лівої руки.
      </p>

      <div className="flex gap-2">
        <button
          type="button"
          onClick={handleSubmit}
          disabled={!ready || exporting || busy}
          className="flex items-center gap-2 rounded-lg bg-accent px-4 py-2.5 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-50"
        >
          {exporting || busy ? <Spinner /> : <Check className="h-4 w-4" />}
          Взяти ноти з редактора
        </button>

        <button
          type="button"
          onClick={() => setStarted(false)}
          className="flex items-center gap-2 rounded-lg border border-ink/15 px-4 py-2.5 text-sm text-muted transition hover:border-accent/40 hover:text-ink"
        >
          <RotateCcw className="h-4 w-4" />
          Змінити розмір
        </button>
      </div>
    </div>
  )
}