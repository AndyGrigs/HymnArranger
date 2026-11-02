import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

const NAV_COL: { key: string; to: string }[] = [
  { key: 'home',     to: '/'         },
  { key: 'how',      to: '/how'      },
  { key: 'examples', to: '/examples' },
  { key: 'support',  to: '/support'  },
]

const ACCOUNT_COL: { key: string; to: string }[] = [
  { key: 'login',    to: '/login'    },
  { key: 'register', to: '/register' },
  { key: 'myWorks',  to: '/works'    },
]

function StaveIcon() {
  const { t } = useTranslation()
  return (
    <img
      src="/icons/accordion.svg"
      alt={t('nav.accordionAlt')}
      title={t('nav.iconCredit')}
      className="h-8 w-auto shrink-0 object-contain"
    />
  )
}

export function Footer() {
  const { t } = useTranslation()
  const year = new Date().getFullYear()

  return (
    <footer className="mt-auto border-t border-[#e3e1da] bg-[#f6f5f1]">
      <div className="mx-auto max-w-7xl px-8 py-12">
        <div className="grid grid-cols-1 gap-10 sm:grid-cols-[1fr_auto_auto]">

          {/* Brand block */}
          <div className="max-w-xs">
            <Link to="/" className="inline-flex items-center gap-2.5">
              <StaveIcon />
              <span className="font-display text-[21px] font-semibold tracking-[.01em] text-ink">
                Hymn<span className="text-accent">Arranger</span>
              </span>
            </Link>
            <p className="mt-3.5 text-sm leading-relaxed text-[#767c86]">
              {t('nav.footer.tagline')}
            </p>
          </div>

          {/* Navigation column */}
          <div>
            <h3 className="mb-3.5 font-mono text-[10.5px] uppercase tracking-[.14em] text-[#a0a4ac]">
              {t('nav.footer.navigation')}
            </h3>
            <ul className="space-y-2.5">
              {NAV_COL.map(({ key, to }) => (
                <li key={key}>
                  <Link
                    to={to}
                    className="text-sm text-[#5a6070] transition hover:text-accent"
                  >
                    {t(`nav.${key}`)}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Account column */}
          <div>
            <h3 className="mb-3.5 font-mono text-[10.5px] uppercase tracking-[.14em] text-[#a0a4ac]">
              {t('nav.footer.account')}
            </h3>
            <ul className="space-y-2.5">
              {ACCOUNT_COL.map(({ key, to }) => (
                <li key={key}>
                  <Link
                    to={to}
                    className="text-sm text-[#5a6070] transition hover:text-accent"
                  >
                    {t(`nav.${key}`)}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="mt-10 flex flex-wrap items-center justify-between gap-3 border-t border-[#e3e1da] pt-6">
          <p className="text-[12.5px] text-[#a0a4ac]">
            {t('nav.footer.rights', { year })}
          </p>
          <p className="text-[12px] text-[#b3b7be]">
            {t('nav.footer.iconBy')}{' '}
            <a
              href="https://commons.wikimedia.org/wiki/File:Accordion_in_SVG_format_(vector).svg"
              target="_blank"
              rel="noopener noreferrer"
              className="underline hover:text-accent"
            >
              Zero Gravity
            </a>
            ,{' '}
            <a
              href="https://creativecommons.org/licenses/by-sa/3.0"
              target="_blank"
              rel="noopener noreferrer"
              className="underline hover:text-accent"
            >
              CC BY-SA 3.0
            </a>
            , {t('nav.footer.viaCommons')}
          </p>
          <p className="text-[12px] text-[#b3b7be]">
            {t('nav.footer.madeWithLove')}
          </p>
        </div>
      </div>
    </footer>
  )
}
