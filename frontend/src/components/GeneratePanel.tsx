import { Dice5, Wand2 } from 'lucide-react'
import { Link } from 'react-router-dom'
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
  strophes: number
  onStrophesChange: (value: number) => void
  coda: boolean
  onCodaChange: (value: boolean) => void
  onGenerate: () => void
  loading: boolean
  isLoggedIn?: boolean
  /** Вбудований режим: рендерить вміст без Card-обгортки (для панелі Налаштування). */
  bare?: boolean
}

const MODES: { id: Mode; label: string; hint: string }[] = [
  { id: 'suite',  label: 'Тема з варіаціями', hint: "готова п'єса з дев'яти розділів"  },
  { id: 'preset', label: 'Одна фактура',       hint: 'конкретний пресет на весь гімн'  },
  { id: 'merge',  label: 'Порівняння',          hint: 'усі доступні пресети підряд'     },
  // Тимчасово вимкнено — стильовий модуль потребує доопрацювання
  // { id: 'style',  label: 'Стиль Сакали',        hint: 'строфи, хроматичні зв\'язки, кода' },
]

export function GeneratePanel(props: Props) {
  const { analysis, mode, loading, bare, isLoggedIn } = props

  const body = (
    <>
      <div className="grid gap-2 grid-cols-2">
        {MODES.map((item) => {
          const active = mode === item.id
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => props.onModeChange(item.id)}
              className={`rounded-[10px] border p-[11px_13px] text-left transition ${
                active
                  ? 'border-accent bg-tint'
                  : 'border-[#e3e1da] bg-white hover:border-[#b6bac2]'
              }`}
            >
              <span className="block text-[13.5px] font-semibold text-ink">{item.label}</span>
              <span className="mt-0.5 block text-xs text-[#6b717a]">{item.hint}</span>
            </button>
          )
        })}
      </div>

      {mode === 'preset' && (
        <label className="mt-5 block">
          <span className="font-mono text-[10.5px] uppercase tracking-[.13em] text-[#8a9099]">
            Пресет · доступно для розміру {analysis.meter}
          </span>
          <select
            value={props.preset}
            onChange={(e) => props.onPresetChange(e.target.value)}
            className="mt-1.5 w-full rounded-lg border border-[#dcdad2] bg-white px-3 py-2 text-[13.5px] text-ink outline-none focus:border-accent"
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
        <div className="mt-5 space-y-3.5 border-t border-[#ecebe6] pt-4.5">
          <label className="flex items-start gap-2.25 text-[13.5px] leading-[1.45] text-[#3a3f47]">
            <input
              type="checkbox"
              checked={props.varyBass}
              onChange={(e) => props.onVaryBassChange(e.target.checked)}
              className="mt-0.5 h-3.75 w-3.75 accent-accent"
            />
            Чергувати фактуру лівої руки між розділами
          </label>

          <div>
            <span className="font-mono text-[10.5px] uppercase tracking-[.13em] text-[#8a9099]">
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
                className="min-w-0 flex-1 rounded-lg border border-[#dcdad2] bg-white px-2.75 py-2 text-[13.5px] text-ink outline-none focus:border-accent"
              />
              <button
                type="button"
                onClick={() => props.onSeedChange(Math.floor(Math.random() * 100000))}
                className="flex items-center gap-1.5 rounded-lg border border-[#dcdad2] bg-white px-2.75 py-2 text-[13px] text-[#454a52] transition hover:border-accent hover:text-accent"
              >
                <Dice5 className="h-3.5 w-3.5" />
                Інше
              </button>
            </div>
            <p className="mt-1.75 text-xs leading-normal text-[#8a9099]">
              Однакове зерно завжди дає однаковий результат.
            </p>
          </div>
        </div>
      )}

      {mode === 'style' && (
        <div className="mt-5 space-y-3 border-t border-[#ecebe6] pt-4.5">
          <label className="block">
            <span className="font-mono text-[10.5px] uppercase tracking-[.13em] text-[#8a9099]">
              Кількість строф
            </span>
            <select
              value={props.strophes}
              onChange={(e) => props.onStrophesChange(Number(e.target.value))}
              className="mt-1.5 w-full rounded-lg border border-[#dcdad2] bg-white px-3 py-2 text-[13.5px] text-ink outline-none focus:border-accent"
            >
              {[1, 2, 3, 4, 5].map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
          </label>

          <label className="flex items-start gap-2.25 text-[13.5px] leading-[1.45] text-[#3a3f47]">
            <input
              type="checkbox"
              checked={props.coda}
              onChange={(e) => props.onCodaChange(e.target.checked)}
              className="mt-0.5 h-3.75 w-3.75 accent-accent"
            />
            Додати коду (хроматичний спуск)
          </label>
        </div>
      )}

      <button
        type="button"
        onClick={props.onGenerate}
        disabled={loading}
        className="mt-5 flex w-full items-center justify-center gap-2.25 rounded-[10px] bg-accent py-3.25 text-[14.5px] font-medium tracking-[.01em] text-white transition hover:brightness-110 disabled:opacity-50"
      >
        {loading ? <Spinner /> : <Wand2 className="h-3.75 w-3.75" />}
        {loading ? 'Генерую…' : 'Аранжувати'}
      </button>

      {!isLoggedIn && (
        <p className="mt-2.5 text-center text-xs leading-normal text-[#8a9099]">
          <Link to="/login" className="text-accent hover:underline">Увійди</Link>{' '}
          або{' '}
          <Link to="/register" className="text-accent hover:underline">зареєструйся</Link>
          , щоб зберегти результат.
        </p>
      )}
    </>
  )

  if (bare) return <div>{body}</div>
  return <Card title="Аранжування">{body}</Card>
}
