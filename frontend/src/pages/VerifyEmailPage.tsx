import { useEffect, useState, FormEvent } from 'react'
import { useSearchParams, useLocation, Link } from 'react-router-dom'
import { Mail, CheckCircle2, XCircle } from 'lucide-react'
import { api, ApiError } from '../api'
import { Spinner } from '../components/ui/Spinner'

type Stage = 'verifying' | 'success' | 'error' | 'resend'

export function VerifyEmailPage() {
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
        setErrorMsg(err instanceof ApiError ? err.message : 'Не вдалося підтвердити пошту')
        setStage('error')
      })
  }, [token])

  async function handleResend(e: FormEvent) {
    e.preventDefault()
    setResendLoading(true)
    setErrorMsg('')
    try {
      await api.resendVerification(email)
      setResendDone(true)
    } catch (err) {
      setErrorMsg(err instanceof ApiError ? err.message : 'Не вдалося надіслати лист')
    } finally {
      setResendLoading(false)
    }
  }

  if (stage === 'verifying') {
    return (
      <div className="mx-auto max-w-md px-6 py-24 text-center">
        <Spinner className="mx-auto h-8 w-8" />
        <p className="mt-4 text-sm text-muted">Перевіряємо токен…</p>
      </div>
    )
  }

  if (stage === 'success') {
    return (
      <div className="mx-auto max-w-md px-6 py-24 text-center">
        <CheckCircle2 className="mx-auto h-12 w-12 text-green-500" />
        <h1 className="mt-4 font-display text-2xl font-bold text-ink">Пошту підтверджено</h1>
        <p className="mt-2 text-sm text-muted">Тепер можеш увійти у свій акаунт.</p>
        <Link
          to="/login"
          className="mt-6 inline-flex items-center gap-2 rounded-lg bg-accent px-5 py-2.5 text-sm font-medium text-white transition hover:opacity-90"
        >
          Увійти
        </Link>
      </div>
    )
  }

  if (stage === 'error') {
    return (
      <div className="mx-auto max-w-md px-6 py-24 text-center">
        <XCircle className="mx-auto h-12 w-12 text-accent" />
        <h1 className="mt-4 font-display text-2xl font-bold text-ink">Помилка підтвердження</h1>
        <p className="mt-2 text-sm text-muted">{errorMsg}</p>
        <button
          type="button"
          onClick={() => { setStage('resend'); setErrorMsg('') }}
          className="mt-6 text-sm text-accent hover:underline"
        >
          Надіслати новий лист
        </button>
      </div>
    )
  }

  // stage === 'resend' — shown right after registration or when user clicks "resend"
  return (
    <div className="mx-auto max-w-md px-6 py-16 text-center">
      <Mail className="mx-auto h-10 w-10 text-accent/60" />
      <h1 className="mt-4 font-display text-2xl font-bold text-ink">Перевірте пошту</h1>
      <p className="mt-2 text-sm text-muted">
        На вашу адресу надіслано лист із посиланням для підтвердження.
        Якщо лист не прийшов — введіть адресу нижче і натисніть «Надіслати ще раз».
      </p>

      {resendDone ? (
        <div className="mt-6 rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">
          Лист надіслано. Перевірте також папку зі спамом.
        </div>
      ) : (
        <form onSubmit={handleResend} className="mt-6 space-y-4 text-left">
          <div>
            <label className="mb-1 block text-sm text-muted" htmlFor="email">Ваша пошта</label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-ink/15 bg-white px-3 py-2 text-sm"
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
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-accent px-4 py-2.5 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-50"
          >
            {resendLoading ? <Spinner /> : <Mail className="h-4 w-4" />}
            {resendLoading ? 'Надсилаю…' : 'Надіслати ще раз'}
          </button>
        </form>
      )}

      <div className="mt-5 text-sm text-muted">
        <Link to="/login" className="text-accent hover:underline">Повернутись до входу</Link>
      </div>
    </div>
  )
}
