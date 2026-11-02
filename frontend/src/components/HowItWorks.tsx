import { useTranslation } from 'react-i18next'
import { Upload, PenLine, Search, Wand2, FileOutput, ArrowRight } from 'lucide-react'

const STEPS = [
  { Icon: Upload,     key: 'step1' },
  { Icon: Search,     key: 'step2' },
  { Icon: Wand2,      key: 'step3' },
  { Icon: FileOutput, key: 'step4' },
] as const

interface Props {
  onStart: () => void
}

export function HowItWorks({ onStart }: Props) {
  const { t } = useTranslation()
  return (
    <div className="mx-auto w-full max-w-5xl px-4 pb-16 pt-10 sm:px-6 sm:pt-14">
      <div className="max-w-2xl">
        <h1 className="font-display text-3xl font-bold leading-tight text-ink sm:text-4xl">
          {t('home.how.title')}
        </h1>
        <p className="mt-4 text-base leading-relaxed text-muted">
          {t('home.how.intro')}
        </p>
      </div>

      <div className="mt-10 grid gap-4 sm:grid-cols-2">
        {STEPS.map(({ Icon, key }) => (
          <div
            key={key}
            className="rounded-2xl border border-ink/10 bg-white p-5 shadow-sm sm:p-6"
          >
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-accent/10">
              <Icon className="h-5 w-5 text-accent" />
            </div>
            <h2 className="mt-4 font-display text-lg text-ink">{t(`home.how.${key}Title`)}</h2>
            <p className="mt-2 text-sm leading-relaxed text-muted">{t(`home.how.${key}Text`)}</p>
          </div>
        ))}
      </div>

      <div className="mt-10 flex items-center gap-3 rounded-2xl border border-ink/10 bg-white/60 px-5 py-4 backdrop-blur-sm sm:px-6">
        <PenLine className="h-5 w-5 shrink-0 text-accent" />
        <p className="flex-1 text-sm text-ink/70">
          {t('home.how.noFile')}
        </p>
        <button
          type="button"
          onClick={onStart}
          className="flex shrink-0 items-center gap-1.5 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white transition hover:opacity-90"
        >
          {t('home.how.start')}
          <ArrowRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
}
