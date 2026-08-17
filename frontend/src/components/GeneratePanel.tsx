import { Dice5, Wand2 } from 'lucide-react'
import type { AnalyzeOut } from '../api'
import type { Mode } from '../hooks/useArrangement'
import { Card } from './ui/Card'
import { Spinner } from './ui/Spinner'

interface Props {
  analysis: AnalyzeOut
  mode: Mode
  onModeChange: (mode: Mode) => void
  preset: string
  onPresetChange: (preset: string) => void
  seed: number | null
  onSeedChange: (seed: number | null) => void
  varyBass: boolean
  onVaryBassChange: (value: boolean) => void
  onGenerate: () => void
  loading: boolean
  /** Вбудований режим: рендерить вміст без Card-обгортки (для панелі Налаштування). */
  bare?: boolean
}

const MODES: { id: Mode; label: string; hint: string }[] = [
  { id: 'suite',  label: 'Тема з варіаціями', hint: "готова п'єса з дев'яти розділів"  },
  { id: 'preset', label: 'Одна фактура',       hint: 'конкретний пресет на весь гімн'  },
  { id: 'merge',  label: 'Порівняння',          hint: 'усі доступні пресети підряд'     },
]

export function GeneratePanel(props: Props) {
  const { analysis, mode, loading, bare } = props

  const body = (
    <>
      <div className="grid gap-2 grid-cols-1 sm:grid-cols-3">
        {MODES.map((item) => {
          const active = mode === item.id
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => props.onModeChange(item.id)}
              className={`rounded-lg border p-3 text-left transition ${
                active
                  ? 'border-accent bg-accent/5'
                  : 'border-ink/10 hover:border-accent/40'
              }`}
            >
              <span className="block text-sm font-medium">{item.label}</span>
              <span className="mt-0.5 block text-xs text-muted">{item.hint}</span>
            </button>
          )
        })}
      </div>

      {mode === 'preset' && (
        <label className="mt-5 block">
          <span className="text-xs uppercase tracking-wide text-muted">
            Пресет · доступно для розміру {analysis.meter}
          </span>
          <select
            value={props.preset}
            onChange={(e) => props.onPresetChange(e.target.value)}
            className="mt-1.5 w-full rounded border border-ink/15 bg-white px-3 py-2 text-sm"
          >
            {analysis.presets.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} — {p.tempo} уд/хв
              </option>
            ))}
          </select>
        </label>
      )}

      {mode === 'suite' && (
        <div className="mt-5 space-y-3">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={props.varyBass}
              onChange={(e) => props.onVaryBassChange(e.target.checked)}
              className="h-4 w-4 accent-accent"
            />
            Чергувати фактуру лівої руки між розділами
          </label>

          <div>
            <span className="text-xs uppercase tracking-wide text-muted">
              Зерно генерації
            </span>
            <div className="mt-1.5 flex gap-2">
              <input
                type="number"
                value={props.seed ?? ''}
                placeholder="випадкове"
                onChange={(e) =>
                  props.onSeedChange(e.target.value === '' ? null : Number(e.target.value))
                }
                className="w-40 rounded border border-ink/15 bg-white px-3 py-2 text-sm"
              />
              <button
                type="button"
                onClick={() => props.onSeedChange(Math.floor(Math.random() * 100000))}
                className="flex items-center gap-1.5 rounded border border-ink/15 px-3 py-2 text-sm text-muted transition hover:border-accent/40 hover:text-ink"
              >
                <Dice5 className="h-4 w-4" />
                Інше
              </button>
            </div>
            {/* Те саме зерно дає той самий порядок розділів — це важливо,
                щоб результат у записці можна було відтворити. */}
            <p className="mt-1 text-xs text-muted">
              Однакове зерно завжди дає однаковий результат.
            </p>
          </div>
        </div>
      )}

      <button
        type="button"
        onClick={props.onGenerate}
        disabled={loading}
        className="mt-6 flex w-full items-center justify-center gap-2 rounded-lg bg-accent px-4 py-3 font-medium text-white transition hover:opacity-90 disabled:opacity-50"
      >
        {loading ? <Spinner /> : <Wand2 className="h-4 w-4" />}
        {loading ? 'Генерую…' : 'Аранжувати'}
      </button>
    </>
  )

  if (bare) return <div>{body}</div>
  return <Card title="Аранжування">{body}</Card>
}