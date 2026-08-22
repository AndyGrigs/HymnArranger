import { useState, FormEvent } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { LogIn } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import { ApiError } from '../api'
import { Spinner } from '../components/ui/Spinner'

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await login(email, password)
      navigate('/')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Не вдалося увійти')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-md px-6 py-16">
      <h1 className="font-display text-2xl font-bold text-ink">Вхід</h1>
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
            value={password}
            onChange={(e) => setPassword(e.target.value)}
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
          {loading ? <Spinner /> : <LogIn className="h-4 w-4" />}
          {loading ? 'Входжу…' : 'Увійти'}
        </button>
      </form>

      <div className="mt-4 flex justify-between text-sm">
        <Link to="/register" className="text-accent hover:underline">Зареєструватись</Link>
        <Link to="/forgot-password" className="text-accent hover:underline">Забув пароль</Link>
      </div>
    </div>
  )
}
