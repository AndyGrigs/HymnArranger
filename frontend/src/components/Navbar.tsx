import { Moon, User } from 'lucide-react'

const NAV_LINKS = ['Головна', 'Як це працює', 'Приклади', 'Підтримка']

export function Navbar() {
  return (
    <nav className="sticky top-0 z-50 border-b border-ink/10 bg-paper/90 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-7xl items-center px-6">
        <div className="flex items-center gap-2">
          <span className="text-2xl leading-none">🪗</span>
          <span className="font-display text-lg font-bold">
            <span className="text-ink">Hymn</span>
            <span className="text-accent">Arranger</span>
          </span>
        </div>

        <ul className="ml-10 hidden items-center gap-7 md:flex">
          {NAV_LINKS.map((link, i) => (
            <li key={link}>
              <a
                href="#"
                className={
                  i === 0
                    ? 'border-b-2 border-accent pb-0.5 text-sm font-medium text-accent'
                    : 'text-sm text-ink/55 transition hover:text-ink'
                }
              >
                {link}
              </a>
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
            className="flex items-center gap-2 rounded-full border border-ink/15 bg-white/50 px-3 py-1.5 text-sm transition hover:bg-ink/5"
          >
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-ink/10">
              <User className="h-3.5 w-3.5 text-ink/60" />
            </span>
            <span className="text-ink/65">Вихід</span>
          </button>
        </div>
      </div>
    </nav>
  )
}
