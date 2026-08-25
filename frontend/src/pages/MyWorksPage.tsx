import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Trash2, Eye, X, Music, Pencil, Check, Search, ChevronLeft, ChevronRight, RotateCcw } from 'lucide-react'
import { useAuth } from '../hooks/useAuth'
import { api, ApiError, type WorkSummary, type WorkDetail } from '../api'
import { Spinner } from '../components/ui/Spinner'

const AbcPaper = lazy(() => import('../components/AbcPaper').then(m => ({ default: m.AbcPaper })))

const PAGE_SIZE = 10

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
  return <Suspense fallback={<div className="flex justify-center py-12"><Spinner /></div>}><AbcPaper abc={abc} /></Suspense>
}

export function MyWorksPage() {
  const { token } = useAuth()
  const navigate = useNavigate()

  const [works, setWorks] = useState<WorkSummary[] | null>(null)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState<WorkDetail | null>(null)
  const [selectedLoading, setSelectedLoading] = useState(false)
  const [deletingId,        setDeletingId]        = useState<string | null>(null)
  const [renamingId,        setRenamingId]        = useState<string | null>(null)
  const [renameValue,       setRenameValue]       = useState('')
  const [renamingLoadingId, setRenamingLoadingId] = useState<string | null>(null)

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  useEffect(() => {
    if (!token) return
    let cancelled = false
    setLoading(true)
    api.listWorks(token, { search: search || undefined, page, pageSize: PAGE_SIZE })
      .then((data) => {
        if (!cancelled) {
          setWorks(data.items)
          setTotal(data.total)
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : 'Не вдалося завантажити роботи')
      })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [token, search, page])

  function handleSearchChange(value: string) {
    setSearchInput(value)
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      setSearch(value)
      setPage(1)
    }, 350)
  }

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

  function startRename(id: string, currentTitle: string) {
    setRenamingId(id)
    setRenameValue(currentTitle)
  }

  async function handleRename(id: string) {
    const title = renameValue.trim()
    if (!title || !token) return
    setRenamingLoadingId(id)
    try {
      const updated = await api.renameWork(token, id, title)
      setWorks((prev) => prev?.map((w) => w.id === id ? { ...w, title: updated.title } : w) ?? null)
      setRenamingId(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Не вдалося перейменувати роботу')
    } finally {
      setRenamingLoadingId(null)
    }
  }

  async function handleDelete(id: string) {
    if (!token) return
    if (!confirm('Видалити цю роботу? Дію не можна скасувати.')) return
    setDeletingId(id)
    try {
      await api.deleteWork(token, id)
      setWorks((prev) => prev?.filter((w) => w.id !== id) ?? null)
      setTotal((t) => t - 1)
      if (selected?.id === id) setSelected(null)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Не вдалося видалити роботу')
    } finally {
      setDeletingId(null)
    }
  }

  async function handleResume(id: string) {
    if (!token) return
    setSelectedLoading(true)
    setError(null)
    try {
      const detail = await api.getWork(token, id)
      if (!detail.source_abc) return
      navigate('/', {
        state: {
          resumeAbc: detail.source_abc,
          resumeTitle: detail.title,
          resumeParams: detail.input_params,
        },
      })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Не вдалося відкрити роботу')
    } finally {
      setSelectedLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-4xl px-6 py-12">
      <h1 className="font-display text-2xl font-bold text-ink">Мої роботи</h1>

      {/* Search */}
      <div className="relative mt-5 max-w-sm">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
        <input
          type="search"
          placeholder="Пошук за назвою…"
          value={searchInput}
          onChange={(e) => handleSearchChange(e.target.value)}
          className="w-full rounded-xl border border-ink/15 bg-white py-2 pl-9 pr-3 text-sm text-ink placeholder:text-muted outline-none focus:border-accent focus:ring-1 focus:ring-accent/30"
        />
      </div>

      {error && (
        <div className="mt-4 rounded-xl border border-accent/30 bg-accent/5 px-4 py-3 text-sm text-accent">
          {error}
        </div>
      )}

      {loading ? (
        <div className="mt-8 flex justify-center"><Spinner /></div>
      ) : !works || works.length === 0 ? (
        <p className="mt-6 text-sm text-muted">
          {search
            ? 'За вашим запитом нічого не знайдено.'
            : <>Тут ще немає збережених робіт. Згенеруй аранжування на{' '}
                <button type="button" onClick={() => navigate('/')} className="text-accent hover:underline">
                  головній сторінці
                </button>{' '}
                — воно з'явиться тут автоматично.</>
          }
        </p>
      ) : (
        <>
          <ul className="mt-6 divide-y divide-ink/10 rounded-2xl border border-ink/10 bg-white">
            {works.map((w) => (
              <li key={w.id} className="flex items-center gap-3 px-5 py-4">
                <div className="min-w-0 flex-1">
                  {renamingId === w.id ? (
                    <form
                      onSubmit={(e) => { e.preventDefault(); handleRename(w.id) }}
                      className="flex items-center gap-1.5"
                    >
                      <input
                        autoFocus
                        value={renameValue}
                        onChange={(e) => setRenameValue(e.target.value)}
                        onKeyDown={(e) => { if (e.key === 'Escape') setRenamingId(null) }}
                        maxLength={255}
                        className="min-w-0 flex-1 rounded border border-accent/40 px-2 py-0.5 text-sm font-medium text-ink outline-none focus:border-accent"
                      />
                      <button
                        type="submit"
                        disabled={renamingLoadingId === w.id || !renameValue.trim()}
                        className="flex h-6 w-6 items-center justify-center rounded text-accent hover:bg-accent/10 disabled:opacity-40"
                      >
                        {renamingLoadingId === w.id ? <Spinner className="h-3.5 w-3.5" /> : <Check className="h-3.5 w-3.5" />}
                      </button>
                      <button
                        type="button"
                        onClick={() => setRenamingId(null)}
                        className="flex h-6 w-6 items-center justify-center rounded text-muted hover:bg-ink/5"
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </form>
                  ) : (
                    <>
                      <p className="truncate font-medium text-ink">{w.title}</p>
                      <p className="text-xs text-muted">{new Date(w.created_at).toLocaleString('uk-UA')}</p>
                    </>
                  )}
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <button
                    type="button"
                    onClick={() => startRename(w.id, w.title)}
                    disabled={renamingId !== null}
                    aria-label="Перейменувати"
                    className="flex h-7 w-7 items-center justify-center rounded-lg border border-ink/15 text-ink/50 transition hover:bg-ink/5 hover:text-ink disabled:opacity-30"
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </button>
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
                    onClick={() => handleResume(w.id)}
                    disabled={!w.has_source}
                    title="Продовжити роботу з цією мелодією"
                    className="flex items-center gap-1.5 rounded-lg border border-ink/15 px-3 py-1.5 text-sm text-ink/70 transition hover:bg-ink/5 disabled:opacity-30"
                  >
                    <RotateCcw className="h-3.5 w-3.5" />
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

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="mt-5 flex items-center justify-between text-sm">
              <span className="text-muted">
                Показано {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, total)} з {total}
              </span>
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => setPage((p) => p - 1)}
                  disabled={page === 1}
                  className="flex h-8 w-8 items-center justify-center rounded-lg border border-ink/15 text-ink/60 transition hover:bg-ink/5 disabled:opacity-30"
                  aria-label="Попередня сторінка"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>

                {Array.from({ length: totalPages }, (_, i) => i + 1)
                  .filter((p) => p === 1 || p === totalPages || Math.abs(p - page) <= 1)
                  .reduce<(number | '…')[]>((acc, p, idx, arr) => {
                    if (idx > 0 && p - (arr[idx - 1] as number) > 1) acc.push('…')
                    acc.push(p)
                    return acc
                  }, [])
                  .map((p, i) =>
                    p === '…' ? (
                      <span key={`ellipsis-${i}`} className="px-1 text-muted">…</span>
                    ) : (
                      <button
                        key={p}
                        type="button"
                        onClick={() => setPage(p as number)}
                        className={`flex h-8 w-8 items-center justify-center rounded-lg border text-sm transition ${
                          page === p
                            ? 'border-accent bg-accent text-white'
                            : 'border-ink/15 text-ink/70 hover:bg-ink/5'
                        }`}
                      >
                        {p}
                      </button>
                    )
                  )
                }

                <button
                  type="button"
                  onClick={() => setPage((p) => p + 1)}
                  disabled={page === totalPages}
                  className="flex h-8 w-8 items-center justify-center rounded-lg border border-ink/15 text-ink/60 transition hover:bg-ink/5 disabled:opacity-30"
                  aria-label="Наступна сторінка"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {(selected || selectedLoading) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-4">
          <div className="max-h-[85vh] w-full max-w-3xl overflow-auto rounded-2xl bg-white shadow-xl">
            <div className="flex items-center justify-between border-b border-ink/10 px-5 py-3">
              <span className="flex items-center gap-2 font-semibold text-ink/80">
                <Music className="h-4 w-4" />
                {selected?.title ?? 'Завантаження…'}
              </span>
              <div className="flex items-center gap-2">
                {selected?.source_abc && (
                  <button
                    type="button"
                    onClick={() => navigate('/', {
                      state: {
                        resumeAbc: selected.source_abc,
                        resumeTitle: selected.title,
                        resumeParams: selected.input_params,
                      },
                    })}
                    className="flex items-center gap-1.5 rounded-lg border border-ink/15 px-3 py-1.5 text-sm text-ink/70 transition hover:bg-ink/5"
                  >
                    <RotateCcw className="h-3.5 w-3.5" />
                    Продовжити роботу
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => setSelected(null)}
                  aria-label="Закрити"
                  className="rounded-full p-1.5 text-ink/50 hover:bg-ink/5 hover:text-ink"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
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
