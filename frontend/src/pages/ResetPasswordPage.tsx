import { useState, FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { KeyRound } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { api, ApiError } from '../api'
import { Spinner } from '../components/ui/Spinner'

const INPUT = 'w-full rounded-lg border border-[#dcdad2] bg-white px-4 py-3 text-[14.5px] outline-none transition focus:border-accent'

export function ResetPasswordPage() {
  const { t } = useTranslation()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')

  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState(false)
  const [loading, setLoading] = useState(false)

  if (!token) {
    return (
      <div className="flex flex-1 items-center justify-center px-4 py-10">
        <div className="w-full max-w-md rounded-2xl border border-[#e3e1da] bg-white p-8 shadow-sm">
          <h1 className="font-display text-2xl font-bold text-ink">{t('auth.reset.invalidTitle')}</h1>
          <p className="mt-3 text-sm text-muted">
            {t('auth.reset.invalidText')}
          </p>
          <Link to="/forgot-password" className="mt-6 inline-block text-sm text-accent hover:underline">
            {t('auth.reset.requestNew')}
          </Link>
        </div>
      </div>
    )
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)

    if (password !== confirmPassword) {
      setError(t('auth.passwordMismatch'))
      return
    }

    setLoading(true)
    try {
      await api.resetPassword(token!, password)
      setDone(true)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t('auth.reset.failed'))
    } finally {
      setLoading(false)
    }
  }

  if (done) {
    return (
      <div className="flex flex-1 items-center justify-center px-4 py-10">
        <div className="w-full max-w-md rounded-2xl border border-[#e3e1da] bg-white p-8 shadow-sm">
          <h1 className="font-display text-2xl font-bold text-ink">{t('auth.reset.doneTitle')}</h1>
          <p className="mt-3 text-sm text-muted">{t('auth.reset.doneText')}</p>
          <Link to="/login" className="mt-6 inline-block text-sm text-accent hover:underline">
            {t('auth.reset.toLogin')}
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-1 items-center justify-center px-4 py-10">
      <div className="w-full max-w-md rounded-2xl border border-[#e3e1da] bg-white p-8 shadow-sm">
        <h1 className="font-display text-2xl font-bold text-ink">{t('auth.reset.title')}</h1>

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <div>
            <label className="mb-1.5 block text-sm text-muted" htmlFor="password">{t('auth.reset.newPassword')}</label>
            <input
              id="password"
              type="password"
              required
              minLength={8}
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={INPUT}
            />
          </div>
          <div>
            <label className="mb-1.5 block text-sm text-muted" htmlFor="confirmPassword">{t('auth.confirmPassword')}</label>
            <input
              id="confirmPassword"
              type="password"
              required
              minLength={8}
              autoComplete="new-password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className={INPUT}
            />
          </div>

          {error && (
            <div className="rounded-xl border border-accent/30 bg-accent/5 px-4 py-3 text-sm text-accent">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="mt-2 flex w-full items-center justify-center gap-2 rounded-lg bg-accent px-4 py-3 text-[14.5px] font-medium text-white transition hover:opacity-90 disabled:opacity-50"
          >
            {loading ? <Spinner /> : <KeyRound className="h-4 w-4" />}
            {loading ? t('auth.reset.submitting') : t('auth.reset.submit')}
          </button>
        </form>
      </div>
    </div>
  )
}
