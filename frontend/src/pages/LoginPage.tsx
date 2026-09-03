import { useState, FormEvent } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { LogIn } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import { ApiError } from '../api'
import { Spinner } from '../components/ui/Spinner'

const INPUT = 'w-full rounded-lg border border-[#dcdad2] bg-white px-4 py-3 text-[14.5px] outline-none transition focus:border-accent'

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
    <div className="flex flex-1 items-center justify-center px-4 py-10">
      <div className="w-full max-w-md rounded-2xl border border-[#e3e1da] bg-white p-8 shadow-sm">
        <h1 className="font-display text-2xl font-bold text-ink">Вхід</h1>

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
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
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
            {loading ? <Spinner /> : <LogIn className="h-4 w-4" />}
            {loading ? 'Входжу…' : 'Увійти'}
          </button>
        </form>

        <div className="mt-5 flex items-center justify-between text-sm">
          <Link to="/register" className="text-accent hover:underline">Зареєструватись</Link>
          <Link to="/forgot-password" className="text-[#767c86] hover:text-accent hover:underline">Забув пароль</Link>
        </div>
      </div>
    </div>
  )
}
