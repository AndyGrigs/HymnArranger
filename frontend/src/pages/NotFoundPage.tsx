import { Link } from 'react-router-dom'
import { Home, Music4 } from 'lucide-react'
import { useTranslation } from 'react-i18next'

export function NotFoundPage() {
  const { t } = useTranslation()

  return (
    <div className="flex flex-1 items-center justify-center px-4 py-16">
      <div className="w-full max-w-lg text-center">
        {/* Нотний стан з «загубленою» нотою замість цифри */}
        <div className="relative mx-auto w-full max-w-sm">
          <div className="absolute inset-x-0 top-1/2 flex -translate-y-1/2 flex-col gap-3.5 opacity-60" aria-hidden="true">
            {[0, 1, 2, 3, 4].map((i) => (
              <span key={i} className="block h-px bg-[#cfcdc4]" />
            ))}
          </div>
          <p
            className="relative font-display font-medium italic text-accent"
            style={{ fontSize: 112, lineHeight: 1.15, letterSpacing: '-.02em' }}
          >
            <span className="bg-paper px-3">404</span>
          </p>
        </div>

        <h1 className="mt-8 font-display text-2xl font-bold text-ink">{t('nav.notFound.title')}</h1>
        <p className="mx-auto mt-3 max-w-md text-sm leading-relaxed text-muted">{t('nav.notFound.text')}</p>

        <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
          <Link
            to="/"
            className="flex items-center gap-2 rounded-[9px] bg-accent px-5 py-2.5 text-[13.5px] font-medium text-white transition hover:opacity-90"
          >
            <Home className="h-4 w-4" />
            {t('nav.notFound.home')}
          </Link>
          <Link
            to="/examples"
            className="flex items-center gap-2 rounded-[9px] border border-[#dcdad2] bg-white px-5 py-2.5 text-[13.5px] font-medium text-[#454a52] transition hover:border-accent hover:text-accent"
          >
            <Music4 className="h-4 w-4" />
            {t('nav.notFound.examples')}
          </Link>
        </div>
      </div>
    </div>
  )
}
