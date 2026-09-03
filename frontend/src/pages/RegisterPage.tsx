import { useState, FormEvent } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { UserPlus } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import { ApiError } from '../api'
import { Spinner } from '../components/ui/Spinner'

const INPUT = 'w-full rounded-lg border border-[#dcdad2] bg-white px-4 py-3 text-[14.5px] outline-none transition focus:border-accent'

export function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)

    if (password !== confirmPassword) {
      setError('Паролі не збігаються')
      return
    }

    setLoading(true)
    try {
      await register(email, password)
      navigate('/verify-email', { state: { email } })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Не вдалося зареєструватись')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-1 items-center justify-center px-4 py-10">
      <div className="w-full max-w-md rounded-2xl border border-[#e3e1da] bg-white p-8 shadow-sm">
        <h1 className="font-display text-2xl font-bold text-ink">Реєстрація</h1>

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
          <div>
            <label className="mb-1.5 block text-sm text-muted" htmlFor="password">Пароль</label>
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
            <label className="mb-1.5 block text-sm text-muted" htmlFor="confirmPassword">Повторіть пароль</label>
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
            {loading ? <Spinner /> : <UserPlus className="h-4 w-4" />}
            {loading ? 'Реєструю…' : 'Зареєструватись'}
          </button>
        </form>

        <p className="mt-5 text-sm text-muted">
          Вже є акаунт?{' '}
          <Link to="/login" className="text-accent hover:underline">Увійти</Link>
        </p>
      </div>
    </div>
  )
}
