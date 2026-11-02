import { useState } from 'react'
import { User, LogOut, Menu, X } from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAuth } from '../hooks/useAuth'
import { LanguageSwitcher } from './LanguageSwitcher'

const NAV_LINKS: { id: string; to?: string }[] = [
  { id: 'home',      to: '/' },
  { id: 'how',       to: '/how' },
  { id: 'melodies',  to: '/melodies' },
  { id: 'accordion', to: '/accordion' },
  { id: 'examples',  to: '/examples' },
  { id: 'support',   to: '/support' },
]

function StaveIcon() {
  const { t } = useTranslation()
  return (
    <img
      src="/icons/accordion.svg"
      alt={t('nav.accordionAlt')}
      title={t('nav.iconCredit')}
      className="h-9 w-auto shrink-0 object-contain"
    />
  )
}

export function Navbar() {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const location = useLocation()
  const { user, logout } = useAuth()

  function close() { setOpen(false) }

  return (
    <nav className="sticky top-0 z-50 border-b border-[#e3e1da] bg-[rgba(246,245,241,.93)] backdrop-blur-[10px]">
      <div className="mx-auto flex h-17 max-w-7xl items-center gap-10 px-8">

        {/* Logo */}
        <Link to="/" className="flex items-center gap-2.75" onClick={close}>
          <StaveIcon />
          <span className="font-display text-[23px] font-semibold tracking-[.01em] text-ink">
            Hymn<span className="text-accent">Arranger</span>
          </span>
        </Link>

        {/* Desktop nav links */}
        <ul className="hidden items-center gap-7.5 md:flex">
          {NAV_LINKS.map((link) => (
            <li key={link.id}>
              {link.to ? (
                <Link
                  to={link.to}
                  className={`text-sm transition ${
                    location.pathname === link.to
                      ? 'font-medium text-accent'
                      : 'text-[#767c86] hover:text-ink'
                  }`}
                >
                  {t(`nav.${link.id}`)}
                </Link>
              ) : (
                <span className="text-sm text-[#b3b7be]">{t(`nav.${link.id}`)}</span>
              )}
            </li>
          ))}
        </ul>

        {/* Right actions */}
        <div className="ml-auto flex items-center gap-2.5">
          <LanguageSwitcher />
          {user ? (
            <>
              <Link
                to="/works"
                className="hidden rounded-lg px-3 py-1.75 text-sm text-[#454a52] transition hover:bg-[#ecebe6] hover:text-ink sm:block"
              >
                {t('nav.myWorks')}
              </Link>
              <button
                type="button"
                onClick={logout}
                title={t('nav.logout')}
                className="hidden items-center gap-2.25 rounded-full border border-[#dcdad2] bg-white px-3.5 py-1.5 pl-2 text-sm text-[#454a52] transition hover:border-accent hover:text-ink sm:flex"
              >
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-tint">
                  <User className="h-3.25 w-3.25 text-accent" />
                </span>
                <span>{user.email}</span>
                <LogOut className="h-3.5 w-3.5 text-[#767c86]" />
              </button>
            </>
          ) : (
            <>
              <Link
                to="/works"
                className="hidden rounded-lg px-3 py-1.75 text-sm text-[#454a52] transition hover:bg-[#ecebe6] hover:text-ink sm:block"
              >
                {t('nav.myWorks')}
              </Link>
              <Link
                to="/login"
                className="hidden items-center gap-2.25 rounded-full border border-[#dcdad2] bg-white px-3.5 py-1.5 pl-2 text-sm text-[#454a52] transition hover:border-accent hover:text-ink sm:flex"
              >
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-tint">
                  <User className="h-3.25 w-3.25 text-accent" />
                </span>
                {t('nav.login')}
              </Link>
            </>
          )}

          {/* Mobile hamburger */}
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            aria-label={t('nav.menu')}
            className="rounded-full p-2 text-[#454a52] transition hover:bg-[#ecebe6] hover:text-ink md:hidden"
          >
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {open && (
        <div className="border-t border-[#e3e1da] bg-paper px-4 py-3 md:hidden">
          <ul className="space-y-0.5">
            {NAV_LINKS.map((link) => (
              <li key={link.id}>
                {link.to ? (
                  <Link
                    to={link.to}
                    onClick={close}
                    className={`block rounded-lg px-3 py-2.5 text-sm font-medium transition ${
                      location.pathname === link.to
                        ? 'bg-tint text-accent'
                        : 'text-[#454a52] hover:bg-[#ecebe6] hover:text-ink'
                    }`}
                  >
                    {t(`nav.${link.id}`)}
                  </Link>
                ) : (
                  <span className="block rounded-lg px-3 py-2.5 text-sm text-[#b3b7be]">
                    {t(`nav.${link.id}`)}
                  </span>
                )}
              </li>
            ))}
          </ul>
          <div className="mt-3 space-y-2 border-t border-[#e3e1da] pt-3">
            <Link
              to="/works"
              onClick={close}
              className="block rounded-lg px-3 py-2.5 text-sm font-medium text-[#454a52] transition hover:bg-[#ecebe6]"
            >
              {t('nav.myWorks')}
            </Link>
            {user ? (
              <button
                type="button"
                onClick={() => { logout(); close() }}
                className="flex w-full items-center gap-2.25 rounded-full border border-[#dcdad2] bg-white px-3.5 py-1.5 pl-2 text-sm text-[#454a52] transition hover:border-accent"
              >
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-tint">
                  <User className="h-3.25 w-3.25 text-accent" />
                </span>
                <span>{t('nav.logoutWithEmail', { email: user.email })}</span>
              </button>
            ) : (
              <Link
                to="/login"
                onClick={close}
                className="flex items-center gap-2.25 rounded-full border border-[#dcdad2] bg-white px-3.5 py-1.5 pl-2 text-sm text-[#454a52] transition hover:border-accent"
              >
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-tint">
                  <User className="h-3.25 w-3.25 text-accent" />
                </span>
                {t('nav.login')}
              </Link>
            )}
          </div>
        </div>
      )}
    </nav>
  )
}
