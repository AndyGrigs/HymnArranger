import { lazy, Suspense, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Music4, Wand2 } from 'lucide-react'
import { Spinner } from '../components/ui/Spinner'
import { fetchMelodies, type MelodyMeta } from '../lib/melodies'

const AbcPaper = lazy(() => import('../components/AbcPaper').then(m => ({ default: m.AbcPaper })))

export function MelodiesPage() {
  const navigate = useNavigate()
  const [melodies, setMelodies] = useState<MelodyMeta[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<MelodyMeta | null>(null)

  useEffect(() => {
    fetchMelodies()
      .then(setMelodies)
      .catch((err: Error) => setError(err.message))
  }, [])

  // Головна вже вміє підхопити ABC зі стану навігації й одразу його проаналізувати.
  function tryArranging(melody: MelodyMeta) {
    navigate('/', {
      state: { resumeAbc: melody.abc, resumeTitle: melody.title, resumeParams: {} },
    })
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <header className="mb-8">
        <h1 className="font-display text-3xl text-accent">Спробуйте самі</h1>
        <p className="mt-1 text-muted">
          Мелодії з готовою гармонією — оберіть будь-яку й згенеруйте власну партитуру, без реєстрації
        </p>
      </header>

      {error && (
        <p className="rounded-lg border border-accent/30 bg-accent/5 px-4 py-3 text-sm text-accent">
          {error}
        </p>
      )}

      {!melodies && !error && (
        <div className="flex items-center gap-2 py-12 text-muted">
          <Spinner />
          <span className="text-sm">Завантажую список…</span>
        </div>
      )}

      {melodies && melodies.length === 0 && (
        <p className="text-sm text-muted">Мелодій поки немає — незабаром з'являться.</p>
      )}

      {melodies && melodies.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-2">
          {melodies.map((m) => {
            const active = selected?.id === m.id
            return (
              <button
                key={m.id}
                type="button"
                onClick={() => setSelected(m)}
                className={`flex items-start gap-3 rounded-lg border p-4 text-left transition ${
                  active ? 'border-accent bg-accent/5' : 'border-ink/10 bg-white hover:border-accent/40'
                }`}
              >
                <Music4 className="mt-0.5 h-5 w-5 shrink-0 text-accent" />
                <div>
                  <p className="font-medium">{m.title}</p>
                  <p className="mt-0.5 text-xs text-muted">{m.meter} · {m.key}</p>
                  {m.description && <p className="mt-1 text-sm text-muted">{m.description}</p>}
                </div>
              </button>
            )
          })}
        </div>
      )}

      {selected && (
        <div className="mt-6 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="font-display text-xl">{selected.title}</h2>
            <button
              type="button"
              onClick={() => tryArranging(selected)}
              className="flex items-center gap-2 rounded-[9px] border border-accent bg-accent px-4 py-2.5 text-[13.5px] font-medium text-white transition hover:opacity-90"
            >
              <Wand2 className="h-4 w-4" />
              Згенерувати партитуру
            </button>
          </div>
          <Suspense fallback={<div className="flex justify-center py-12"><Spinner /></div>}>
            <AbcPaper abc={selected.abc} />
          </Suspense>
        </div>
      )}
    </div>
  )
}
