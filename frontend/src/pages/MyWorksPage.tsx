import { useEffect, useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { Trash2, Eye, X, Music } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import { api, ApiError, type WorkSummary, type WorkDetail } from '../api'
import { Spinner } from '../components/ui/Spinner'
import { AbcPaper } from '../components/AbcPaper'

/** Converts a saved work's MusicXML to ABC on first open, then displays it. */
function WorkViewer({ musicxml }: { musicxml: string }) {
  const [abc, setAbc] = useState<string | null>(null)
  const [err, setErr] = useState(false)

  useEffect(() => {
    setAbc(null)
    setErr(false)
    api.convertToAbc({ musicxml })
      .then((r) => setAbc(r.abc))
      .catch(() => setErr(true))
  }, [musicxml])

  if (err) return <p className="text-sm text-muted">Не вдалося відобразити партитуру.</p>
  if (abc === null) return <div className="flex justify-center py-12"><Spinner /></div>
  return <AbcPaper abc={abc} />
}

export function MyWorksPage() {
  const { user, token, isLoading: authLoading } = useAuth()
  const navigate = useNavigate()

  const [works, setWorks] = useState<WorkSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<WorkDetail | null>(null)
  const [selectedLoading, setSelectedLoading] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  useEffect(() => {
    if (!token) return
    let cancelled = false
    setLoading(true)
    api.listWorks(token)
      .then((data) => { if (!cancelled) setWorks(data) })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : 'Не вдалося завантажити роботи')
      })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [token])

  async function openWork(id: string) {
    if (!token) return
    setSelectedLoading(true)
    setError(null)
    try {
      setSelected(await api.getWork(token, id))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Не вдалося відкрити роботу')
    } finally {
      setSelectedLoading(false)
    }
  }

  async function handleDelete(id: string) {
    if (!token) return
    if (!confirm('Видалити цю роботу? Дію не можна скасувати.')) return
    setDeletingId(id)
    try {
      await api.deleteWork(token, id)
      setWorks((prev) => prev?.filter((w) => w.id !== id) ?? null)
      if (selected?.id === id) setSelected(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Не вдалося видалити роботу')
    } finally {
      setDeletingId(null)
    }
  }

  if (authLoading) {
    return <div className="flex justify-center py-16"><Spinner /></div>
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return (
    <div className="mx-auto max-w-4xl px-6 py-12">
      <h1 className="font-display text-2xl font-bold text-ink">Мої роботи</h1>

      {error && (
        <div className="mt-4 rounded-xl border border-accent/30 bg-accent/5 px-4 py-3 text-sm text-accent">
          {error}
        </div>
      )}

      {loading ? (
        <div className="mt-8 flex justify-center"><Spinner /></div>
      ) : !works || works.length === 0 ? (
        <p className="mt-6 text-sm text-muted">
          Тут ще немає збережених робіт. Згенеруй аранжування на{' '}
          <button type="button" onClick={() => navigate('/')} className="text-accent hover:underline">
            головній сторінці
          </button>{' '}
          — воно з'явиться тут автоматично.
        </p>
      ) : (
        <ul className="mt-6 divide-y divide-ink/10 rounded-2xl border border-ink/10 bg-white">
          {works.map((w) => (
            <li key={w.id} className="flex items-center justify-between gap-3 px-5 py-4">
              <div className="min-w-0">
                <p className="truncate font-medium text-ink">{w.title}</p>
                <p className="text-xs text-muted">{new Date(w.created_at).toLocaleString('uk-UA')}</p>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <button
                  type="button"
                  onClick={() => openWork(w.id)}
                  className="flex items-center gap-1.5 rounded-lg border border-ink/15 px-3 py-1.5 text-sm text-ink/70 transition hover:bg-ink/5"
                >
                  <Eye className="h-3.5 w-3.5" />
                  Переглянути
                </button>
                <button
                  type="button"
                  onClick={() => handleDelete(w.id)}
                  disabled={deletingId === w.id}
                  className="flex items-center gap-1.5 rounded-lg border border-ink/15 px-3 py-1.5 text-sm text-accent transition hover:bg-accent/5 disabled:opacity-50"
                >
                  {deletingId === w.id ? <Spinner /> : <Trash2 className="h-3.5 w-3.5" />}
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      {(selected || selectedLoading) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-4">
          <div className="max-h-[85vh] w-full max-w-3xl overflow-auto rounded-2xl bg-white shadow-xl">
            <div className="flex items-center justify-between border-b border-ink/10 px-5 py-3">
              <span className="flex items-center gap-2 font-semibold text-ink/80">
                <Music className="h-4 w-4" />
                {selected?.title ?? 'Завантаження…'}
              </span>
              <button
                type="button"
                onClick={() => setSelected(null)}
                aria-label="Закрити"
                className="rounded-full p-1.5 text-ink/50 hover:bg-ink/5 hover:text-ink"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="p-4">
              {selectedLoading || !selected ? (
                <div className="flex justify-center py-12"><Spinner /></div>
              ) : (
                <WorkViewer musicxml={selected.musicxml_content} />
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
