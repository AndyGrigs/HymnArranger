import { useState, FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { Mail } from 'lucide-react'
import { api, ApiError } from '../api'
import { Spinner } from '../components/ui/Spinner'

const INPUT = 'w-full rounded-lg border border-[#dcdad2] bg-white px-4 py-3 text-[14.5px] outline-none transition focus:border-accent'

export function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [sent, setSent] = useState(false)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await api.forgotPassword(email)
      setSent(true)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Не вдалося надіслати лист')
    } finally {
      setLoading(false)
    }
  }

  if (sent) {
    return (
      <div className="flex flex-1 items-center justify-center px-4 py-10">
        <div className="w-full max-w-md rounded-2xl border border-[#e3e1da] bg-white p-8 shadow-sm">
          <h1 className="font-display text-2xl font-bold text-ink">Перевір пошту</h1>
          <p className="mt-3 text-sm text-muted">
            Якщо ця пошта зареєстрована, на неї надіслано лист з інструкціями для відновлення пароля.
            Посилання дійсне 30 хвилин.
          </p>
          <Link to="/login" className="mt-6 inline-block text-sm text-accent hover:underline">
            Повернутись до входу
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-1 items-center justify-center px-4 py-10">
      <div className="w-full max-w-md rounded-2xl border border-[#e3e1da] bg-white p-8 shadow-sm">
        <h1 className="font-display text-2xl font-bold text-ink">Відновлення пароля</h1>
        <p className="mt-2 text-sm text-muted">
          Введи пошту, і ми надішлемо посилання для встановлення нового пароля.
        </p>

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <div>
            <label className="mb-1.5 block text-sm text-muted" htmlFor="email">Пошта</label>
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
            {loading ? <Spinner /> : <Mail className="h-4 w-4" />}
            {loading ? 'Надсилаю…' : 'Надіслати лист'}
          </button>
        </form>

        <Link to="/login" className="mt-5 inline-block text-sm text-[#767c86] hover:text-accent hover:underline">
          Повернутись до входу
        </Link>
      </div>
    </div>
  )
}
