import { AlertTriangle } from 'lucide-react'
import type { AnalyzeOut } from '../api'
import { Card } from './ui/Card'
import { formatKey, offsetToPosition } from '../lib/music'

function Fact({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-muted">{label}</dt>
      <dd className="mt-0.5 font-display text-lg">{value}</dd>
    </div>
  )
}

export function AnalysisPanel({ data }: { data: AnalyzeOut }) {
  const family = data.meter_family === 'compound' ? 'складений' : 'простий'

  return (
    <Card title="Аналіз мелодії">
      <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Fact label="Розмір" value={`${data.meter} (${family})`} />
        <Fact label="Тональність" value={formatKey(data.key)} />
        <Fact label="Тактів" value={data.measures} />
        <Fact
          label="Затакт"
          value={data.pickup_ql > 0 ? `${data.pickup_ql} чв.` : 'немає'}
        />
      </dl>

      {data.warnings.length > 0 && (
        <ul className="mt-5 space-y-2">
          {data.warnings.map((warning, i) => (
            <li
              key={i}
              className="flex items-start gap-2 rounded border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900"
            >
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{warning}</span>
            </li>
          ))}
        </ul>
      )}

      <div className="mt-5">
        <h3 className="text-xs uppercase tracking-wide text-muted">
          Акорди — {data.chords.length} шт. (джерело: {data.chord_source})
        </h3>

        {data.chords.length === 0 ? (
          <p className="mt-2 text-sm text-muted">
            Акордових символів не знайдено. Ліва рука буде порожньою — додай
            позначки акордів у MuseScore і завантаж файл ще раз.
          </p>
        ) : (
          <ol className="mt-2 flex flex-wrap gap-1.5">
            {data.chords.map((chord, i) => {
              const { measure } = offsetToPosition(
                chord.offset,
                data.meter,
                data.pickup_ql,
              )
              return (
                <li
                  key={i}
                  title={`такт ${measure}, зміщення ${chord.offset}`}
                  className="rounded bg-ink/5 px-2 py-1 font-mono text-xs"
                >
                  <span className="text-muted">{measure}</span>
                  <span className="ml-1.5">{chord.figure || '—'}</span>
                </li>
              )
            })}
          </ol>
        )}
      </div>
    </Card>
  )
}