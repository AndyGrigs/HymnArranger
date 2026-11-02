import { ChevronDown } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'

const FAQ_KEYS = ['formats', 'chords', 'warnings', 'save', 'edit', 'upload'] as const

function FaqItem({ q, a }: { q: string; a: string }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="border-b border-ink/10 last:border-0">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-4 py-4 text-left text-sm font-medium text-ink transition hover:text-accent"
      >
        {q}
        <ChevronDown
          className={`h-4 w-4 shrink-0 text-muted transition-transform ${open ? 'rotate-180' : ''}`}
        />
      </button>
      {open && (
        <p className="pb-4 text-sm leading-relaxed text-muted">{a}</p>
      )}
    </div>
  )
}

export function SupportPage() {
  const { t } = useTranslation()
  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <header className="mb-10">
        <h1 className="font-display text-3xl text-accent">{t('support.title')}</h1>
        <p className="mt-1 text-muted">
          {t('support.subtitle')}
        </p>
      </header>

      {/* FAQ */}
      <section className="mb-10">
        <h2 className="mb-4 font-display text-xl text-ink">{t('support.faqTitle')}</h2>
        <div className="rounded-lg border border-ink/10 bg-white px-5">
          {FAQ_KEYS.map((key) => (
            <FaqItem key={key} q={t(`support.faq.${key}Q`)} a={t(`support.faq.${key}A`)} />
          ))}
        </div>
      </section>

      {/* Contact */}
      <section className="mb-10 rounded-lg border border-ink/10 bg-white p-6">
        <h2 className="mb-1 font-display text-xl text-ink">{t('support.contactTitle')}</h2>
        <p className="mb-4 text-sm text-muted">
          {t('support.contactText')}
        </p>
        <a
          href="mailto:andygrigs88@gmail.com"
          className="inline-flex items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white transition hover:bg-accent/90"
        >
          {t('support.contactButton')}
        </a>
      </section>

      {/* Quick links */}
      <section>
        <h2 className="mb-4 font-display text-xl text-ink">{t('support.linksTitle')}</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <Link
            to="/how"
            className="rounded-lg border border-ink/10 bg-white p-4 text-sm transition hover:border-accent/40"
          >
            <p className="font-medium text-ink">{t('support.linkHow')}</p>
            <p className="mt-0.5 text-muted">{t('support.linkHowText')}</p>
          </Link>
          <Link
            to="/examples"
            className="rounded-lg border border-ink/10 bg-white p-4 text-sm transition hover:border-accent/40"
          >
            <p className="font-medium text-ink">{t('support.linkExamples')}</p>
            <p className="mt-0.5 text-muted">{t('support.linkExamplesText')}</p>
          </Link>
        </div>
      </section>
    </div>
  )
}
