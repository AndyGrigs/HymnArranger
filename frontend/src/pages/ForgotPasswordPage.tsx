import { useState, FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { Mail } from 'lucide-react'
import { api, ApiError } from '../api'
import { Spinner } from '../components/ui/Spinner'

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
      <div className="mx-auto max-w-md px-6 py-16">
        <h1 className="font-display text-2xl font-bold text-ink">Перевір пошту</h1>
        <p className="mt-4 text-sm text-muted">
          Якщо ця пошта зареєстрована, на неї надіслано лист з інструкціями для відновлення пароля.
          Посилання дійсне 30 хвилин.
        </p>
        <Link to="/login" className="mt-6 inline-block text-sm text-accent hover:underline">
          Повернутись до входу
        </Link>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-md px-6 py-16">
      <h1 className="font-display text-2xl font-bold text-ink">Відновлення пароля</h1>
      <p className="mt-2 text-sm text-muted">
        Введи пошту, і ми надішлемо посилання для встановлення нового пароля.
      </p>
      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        <div>
          <label className="mb-1 block text-sm text-muted" htmlFor="email">Пошта</label>
          <input
            id="email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-lg border border-ink/15 bg-white px-3 py-2 text-sm"
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
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-accent px-4 py-2.5 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-50"
        >
          {loading ? <Spinner /> : <Mail className="h-4 w-4" />}
          {loading ? 'Надсилаю…' : 'Надіслати лист'}
        </button>
      </form>

      <Link to="/login" className="mt-4 inline-block text-sm text-accent hover:underline">
        Повернутись до входу
      </Link>
    </div>
  )
}
