import { useEffect, useState } from 'react'
import { Music4 } from 'lucide-react'
import { SheetViewer } from '../components/SheetViewer'
import { Spinner } from '../components/ui/Spinner'
import { fetchExampleXml, fetchExamples, type ExampleMeta } from '../lib/examples'

export function ExamplesPage() {
  const [examples, setExamples] = useState<ExampleMeta[] | null>(null)
  const [listError, setListError] = useState<string | null>(null)

  const [selected, setSelected] = useState<ExampleMeta | null>(null)
  const [xml, setXml] = useState<string | null>(null)
  const [loadingXml, setLoadingXml] = useState(false)
  const [xmlError, setXmlError] = useState<string | null>(null)

  useEffect(() => {
    fetchExamples()
      .then(setExamples)
      .catch((err: Error) => setListError(err.message))
  }, [])

  function openExample(example: ExampleMeta) {
    setSelected(example)
    setXml(null)
    setXmlError(null)
    setLoadingXml(true)

    fetchExampleXml(example.file)
      .then(setXml)
      .catch((err: Error) => setXmlError(err.message))
      .finally(() => setLoadingXml(false))
  }

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <header className="mb-8">
        <h1 className="font-display text-3xl text-accent">Приклади аранжувань</h1>
        <p className="mt-1 text-muted">
          Готові партитури — щоб оцінити результат без завантаження власних нот
        </p>
      </header>

      {listError && (
        <p className="rounded-lg border border-accent/30 bg-accent/5 px-4 py-3 text-sm text-accent">
          {listError}
        </p>
      )}

      {!examples && !listError && (
        <div className="flex items-center gap-2 py-12 text-muted">
          <Spinner />
          <span className="text-sm">Завантажую список…</span>
        </div>
      )}

      {examples && examples.length === 0 && (
        <p className="text-sm text-muted">
          Прикладів поки немає — додай файли у <code>public/scores/</code> і
          опиши їх у <code>manifest.json</code>.
        </p>
      )}

      {examples && examples.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-2">
          {examples.map((ex) => {
            const active = selected?.id === ex.id
            return (
              <button
                key={ex.id}
                type="button"
                onClick={() => openExample(ex)}
                className={`flex items-start gap-3 rounded-lg border p-4 text-left transition ${
                  active
                    ? 'border-accent bg-accent/5'
                    : 'border-ink/10 bg-white hover:border-accent/40'
                }`}
              >
                <Music4 className="mt-0.5 h-5 w-5 shrink-0 text-accent" />
                <div>
                  <p className="font-medium">{ex.title}</p>
                  <p className="mt-0.5 text-xs text-muted">
                    {ex.meter} · {ex.key}
                  </p>
                  {ex.description && (
                    <p className="mt-1 text-sm text-muted">{ex.description}</p>
                  )}
                </div>
              </button>
            )
          })}
        </div>
      )}

      {selected && (
        <div className="mt-6 space-y-3">
          <h2 className="font-display text-xl">{selected.title}</h2>

          {loadingXml && (
            <div className="flex items-center gap-2 py-8 text-muted">
              <Spinner />
              <span className="text-sm">Завантажую партитуру…</span>
            </div>
          )}

          {xmlError && (
            <p className="rounded-lg border border-accent/30 bg-accent/5 px-4 py-3 text-sm text-accent">
              {xmlError}
            </p>
          )}

          {xml && <SheetViewer musicxml={xml} />}
        </div>
      )}
    </div>
  )
}
