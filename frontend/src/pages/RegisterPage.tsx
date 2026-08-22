import { useState, FormEvent } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { UserPlus } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import { ApiError } from '../api'
import { Spinner } from '../components/ui/Spinner'

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
      navigate('/')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Не вдалося зареєструватись')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-md px-6 py-16">
      <h1 className="font-display text-2xl font-bold text-ink">Реєстрація</h1>
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
        <div>
          <label className="mb-1 block text-sm text-muted" htmlFor="password">Пароль</label>
          <input
            id="password"
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-lg border border-ink/15 bg-white px-3 py-2 text-sm"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm text-muted" htmlFor="confirmPassword">Повторіть пароль</label>
          <input
            id="confirmPassword"
            type="password"
            required
            minLength={8}
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
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
          {loading ? <Spinner /> : <UserPlus className="h-4 w-4" />}
          {loading ? 'Реєструю…' : 'Зареєструватись'}
        </button>
      </form>

      <div className="mt-4 text-sm text-muted">
        Вже є акаунт?{' '}
        <Link to="/login" className="text-accent hover:underline">Увійти</Link>
      </div>
    </div>
  )
}
