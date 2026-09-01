import { Link } from 'react-router-dom'

const NAV_COL: { label: string; to?: string }[] = [
  { label: 'Головна',      to: '/'    },
  { label: 'Як це працює', to: '/how' },
  { label: 'Приклади'                 },
  { label: 'Підтримка'                },
]

const ACCOUNT_COL: { label: string; to?: string }[] = [
  { label: 'Увійти',       to: '/login'    },
  { label: 'Реєстрація',   to: '/register' },
  { label: 'Мої роботи',   to: '/works'    },
]

function StaveIcon() {
  return (
    <span
      className="flex h-7 w-7 flex-col justify-between rounded-md border border-accent"
      style={{ padding: '5px 4px' }}
    >
      {[0, 1, 2, 3, 4].map((i) => (
        <span key={i} className={`block h-px bg-accent ${i === 2 ? '' : 'opacity-50'}`} />
      ))}
    </span>
  )
}

export function Footer() {
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
              Автоматична гармонізація церковних гімнів. Завантажте мелодію — отримайте
              повну партитуру за секунди.
            </p>
          </div>

          {/* Navigation column */}
          <div>
            <h3 className="mb-3.5 font-mono text-[10.5px] uppercase tracking-[.14em] text-[#a0a4ac]">
              Навігація
            </h3>
            <ul className="space-y-2.5">
              {NAV_COL.map(({ label, to }) => (
                <li key={label}>
                  {to ? (
                    <Link
                      to={to}
                      className="text-sm text-[#5a6070] transition hover:text-accent"
                    >
                      {label}
                    </Link>
                  ) : (
                    <span className="text-sm text-[#b3b7be]">{label}</span>
                  )}
                </li>
              ))}
            </ul>
          </div>

          {/* Account column */}
          <div>
            <h3 className="mb-3.5 font-mono text-[10.5px] uppercase tracking-[.14em] text-[#a0a4ac]">
              Акаунт
            </h3>
            <ul className="space-y-2.5">
              {ACCOUNT_COL.map(({ label, to }) => (
                <li key={label}>
                  {to ? (
                    <Link
                      to={to}
                      className="text-sm text-[#5a6070] transition hover:text-accent"
                    >
                      {label}
                    </Link>
                  ) : (
                    <span className="text-sm text-[#b3b7be]">{label}</span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="mt-10 flex flex-wrap items-center justify-between gap-3 border-t border-[#e3e1da] pt-6">
          <p className="text-[12.5px] text-[#a0a4ac]">
            © {year} HymnArranger. Всі права захищені.
          </p>
          <p className="text-[12px] text-[#b3b7be]">
            Зроблено з любов'ю до церковної музики
          </p>
        </div>
      </div>
    </footer>
  )
}
