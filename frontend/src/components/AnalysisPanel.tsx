import { useTranslation } from 'react-i18next'
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
  const { t } = useTranslation()
  const family = t(data.meter_family === 'compound' ? 'panels.analysis.compound' : 'panels.analysis.simple')

  return (
    <Card title={t('panels.analysis.title')}>
      <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Fact label={t('panels.analysis.meter')} value={t('panels.analysis.meterWithFamily', { meter: data.meter, family })} />
        <Fact label={t('panels.analysis.key')} value={formatKey(data.key)} />
        <Fact label={t('panels.analysis.measures')} value={data.measures} />
        <Fact
          label={t('panels.analysis.pickup')}
          value={data.pickup_ql > 0 ? t('panels.analysis.pickupValue', { n: data.pickup_ql }) : t('panels.analysis.noPickup')}
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
          {t('panels.analysis.chordsHeading', { n: data.chords.length, source: data.chord_source })}
        </h3>

        {data.chords.length === 0 ? (
          <p className="mt-2 text-sm text-muted">
            {t('panels.analysis.noChords')}
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
                  title={t('panels.analysis.chordTitle', { measure, offset: chord.offset })}
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