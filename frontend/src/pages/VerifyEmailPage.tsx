import { useEffect, useState, FormEvent } from 'react'
import { useSearchParams, useLocation, Link } from 'react-router-dom'
import { Mail, CheckCircle2, XCircle } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { api, ApiError } from '../api'
import { Spinner } from '../components/ui/Spinner'

type Stage = 'verifying' | 'success' | 'error' | 'resend'

const INPUT = 'w-full rounded-lg border border-[#dcdad2] bg-white px-4 py-3 text-[14.5px] outline-none transition focus:border-accent'

export function VerifyEmailPage() {
  const { t } = useTranslation()
  const [searchParams] = useSearchParams()
  const location = useLocation()
  const token = searchParams.get('token')
  const prefillEmail: string = (location.state as { email?: string } | null)?.email ?? ''

  const [stage, setStage] = useState<Stage>(token ? 'verifying' : 'resend')
  const [errorMsg, setErrorMsg] = useState('')
  const [email, setEmail] = useState(prefillEmail)
  const [resendLoading, setResendLoading] = useState(false)
  const [resendDone, setResendDone] = useState(false)

  useEffect(() => {
    if (!token) return
    api.verifyEmail(token)
      .then(() => setStage('success'))
      .catch((err) => {
        setErrorMsg(err instanceof ApiError ? err.message : t('auth.verify.failed'))
        setStage('error')
      })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  async function handleResend(e: FormEvent) {
    e.preventDefault()
    setResendLoading(true)
    setErrorMsg('')
    try {
      await api.resendVerification(email)
      setResendDone(true)
    } catch (err) {
      setErrorMsg(err instanceof ApiError ? err.message : t('auth.verify.resendFailed'))
    } finally {
      setResendLoading(false)
    }
  }

  if (stage === 'verifying') {
    return (
      <div className="flex flex-1 items-center justify-center px-4 py-10">
        <div className="w-full max-w-md rounded-2xl border border-[#e3e1da] bg-white p-8 text-center shadow-sm">
          <Spinner className="mx-auto h-8 w-8" />
          <p className="mt-4 text-sm text-muted">{t('auth.verify.checking')}</p>
        </div>
      </div>
    )
  }

  if (stage === 'success') {
    return (
      <div className="flex flex-1 items-center justify-center px-4 py-10">
        <div className="w-full max-w-md rounded-2xl border border-[#e3e1da] bg-white p-8 text-center shadow-sm">
          <CheckCircle2 className="mx-auto h-12 w-12 text-green-500" />
          <h1 className="mt-4 font-display text-2xl font-bold text-ink">{t('auth.verify.successTitle')}</h1>
          <p className="mt-2 text-sm text-muted">{t('auth.verify.successText')}</p>
          <Link
            to="/login"
            className="mt-6 inline-flex items-center gap-2 rounded-lg bg-accent px-5 py-3 text-[14.5px] font-medium text-white transition hover:opacity-90"
          >
            {t('auth.verify.login')}
          </Link>
        </div>
      </div>
    )
  }

  if (stage === 'error') {
    return (
      <div className="flex flex-1 items-center justify-center px-4 py-10">
        <div className="w-full max-w-md rounded-2xl border border-[#e3e1da] bg-white p-8 text-center shadow-sm">
          <XCircle className="mx-auto h-12 w-12 text-accent" />
          <h1 className="mt-4 font-display text-2xl font-bold text-ink">{t('auth.verify.errorTitle')}</h1>
          <p className="mt-2 text-sm text-muted">{errorMsg}</p>
          <button
            type="button"
            onClick={() => { setStage('resend'); setErrorMsg('') }}
            className="mt-6 text-sm text-accent hover:underline"
          >
            {t('auth.verify.resendNew')}
          </button>
        </div>
      </div>
    )
  }

  // stage === 'resend'
  return (
    <div className="flex flex-1 items-center justify-center px-4 py-10">
      <div className="w-full max-w-md rounded-2xl border border-[#e3e1da] bg-white p-8 shadow-sm">
        <div className="text-center">
          <Mail className="mx-auto h-10 w-10 text-accent/60" />
          <h1 className="mt-4 font-display text-2xl font-bold text-ink">{t('auth.verify.checkTitle')}</h1>
          <p className="mt-2 text-sm text-muted">
            {t('auth.verify.checkText')}
          </p>
        </div>

        {resendDone ? (
          <div className="mt-6 rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">
            {t('auth.verify.resendDone')}
          </div>
        ) : (
          <form onSubmit={handleResend} className="mt-6 space-y-4">
            <div>
              <label className="mb-1.5 block text-sm text-muted" htmlFor="email">{t('auth.verify.yourEmail')}</label>
              <input
                id="email"
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className={INPUT}
              />
            </div>
            {errorMsg && (
              <div className="rounded-xl border border-accent/30 bg-accent/5 px-4 py-3 text-sm text-accent">
                {errorMsg}
              </div>
            )}
            <button
              type="submit"
              disabled={resendLoading}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-accent px-4 py-3 text-[14.5px] font-medium text-white transition hover:opacity-90 disabled:opacity-50"
            >
              {resendLoading ? <Spinner /> : <Mail className="h-4 w-4" />}
              {resendLoading ? t('auth.verify.resending') : t('auth.verify.resend')}
            </button>
          </form>
        )}

        <div className="mt-5 text-center text-sm">
          <Link to="/login" className="text-[#767c86] hover:text-accent hover:underline">{t('auth.backToLogin')}</Link>
        </div>
      </div>
    </div>
  )
}
