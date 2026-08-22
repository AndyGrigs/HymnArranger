import { useState } from 'react'
import { Menu, Moon, User, X } from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'

const NAV_LINKS: { id: string; label: string; to?: string }[] = [
  { id: 'home', label: 'Головна', to: '/' },
  { id: 'how',  label: 'Як це працює', to: '/how' },
  { id: 'examples', label: 'Приклади' },
  { id: 'support',  label: 'Підтримка' },
]

export function Navbar() {
  const [open, setOpen] = useState(false)
  const location = useLocation()

  function close() {
    setOpen(false)
  }

  return (
    <nav className="sticky top-0 z-50 border-b border-ink/10 bg-paper/90 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-7xl items-center px-4 sm:px-6">
        <div className="flex items-center gap-2">
          <span className="text-2xl leading-none">🪗</span>
          <span className="font-display text-lg font-bold">
            <span className="text-ink">Hymn</span>
            <span className="text-accent">Arranger</span>
          </span>
        </div>

        <ul className="ml-10 hidden items-center gap-7 md:flex">
          {NAV_LINKS.map((link) => (
            <li key={link.id}>
              {link.to ? (
                <Link
                  to={link.to}
                  className={
                    location.pathname === link.to
                      ? 'border-b-2 border-accent pb-0.5 text-sm font-medium text-accent'
                      : 'text-sm text-ink/55 transition hover:text-ink'
                  }
                >
                  {link.label}
                </Link>
              ) : (
                <span className="text-sm text-ink/30">{link.label}</span>
              )}
            </li>
          ))}
        </ul>

        <div className="ml-auto flex items-center gap-2">
          <button
            type="button"
            aria-label="Тема"
            className="rounded-full p-2 text-ink/50 transition hover:bg-ink/5 hover:text-ink"
          >
            <Moon className="h-4 w-4" />
          </button>
          <button
            type="button"
            className="hidden items-center gap-2 rounded-full border border-ink/15 bg-white/50 px-3 py-1.5 text-sm transition hover:bg-ink/5 sm:flex"
          >
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-ink/10">
              <User className="h-3.5 w-3.5 text-ink/60" />
            </span>
            <span className="text-ink/65">Вихід</span>
          </button>
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            aria-label="Меню"
            className="rounded-full p-2 text-ink/50 transition hover:bg-ink/5 hover:text-ink md:hidden"
          >
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {open && (
        <div className="border-t border-ink/10 bg-paper px-4 py-3 md:hidden">
          <ul className="space-y-0.5">
            {NAV_LINKS.map((link) => (
              <li key={link.id}>
                {link.to ? (
                  <Link
                    to={link.to}
                    onClick={close}
                    className={`block rounded-lg px-3 py-2.5 text-sm font-medium transition ${
                      location.pathname === link.to
                        ? 'bg-accent/5 text-accent'
                        : 'text-ink/65 hover:bg-ink/5 hover:text-ink'
                    }`}
                  >
                    {link.label}
                  </Link>
                ) : (
                  <span className="block rounded-lg px-3 py-2.5 text-sm font-medium text-ink/30">
                    {link.label}
                  </span>
                )}
              </li>
            ))}
          </ul>
          <div className="mt-3 border-t border-ink/10 pt-3">
            {/* <button
              type="button"
              className="flex items-center gap-2 rounded-full border border-ink/15 bg-white/50 px-3 py-1.5 text-sm transition hover:bg-ink/5"
            >
              <span className="flex h-6 w-6 items-center justify-center rounded-full bg-ink/10">
                <User className="h-3.5 w-3.5 text-ink/60" />
              </span>
              <span className="text-ink/65">Вихід</span>
            </button> */}
          </div>
        </div>
      )}
    </nav>
  )
}
