import { useEffect, useRef, useState } from 'react'
import { OpenSheetMusicDisplay } from 'opensheetmusicdisplay'
import { Minus, Plus } from 'lucide-react'
import { Spinner } from './ui/Spinner'

interface Props {
  musicxml: string
}

const ZOOM_MIN = 0.4
const ZOOM_MAX = 1.6
const ZOOM_STEP = 0.1

export function SheetViewer({ musicxml }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const osmdRef = useRef<OpenSheetMusicDisplay | null>(null)
  const [zoom, setZoom] = useState(0.7)
  const [rendering, setRendering] = useState(true)
  const [failed, setFailed] = useState<string | null>(null)

  // Zoom читаємо через ref: інакше довелося б класти його в залежності
  // ефекту завантаження, і кожна зміна масштабу перепарсювала б партитуру.
  const zoomRef = useRef(zoom)
  zoomRef.current = zoom

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    let cancelled = false
    // StrictMode у розробці монтує ефект двічі — без очищення
    // в контейнері опиняється два SVG.
    container.innerHTML = ''
    setRendering(true)
    setFailed(null)

    const osmd = new OpenSheetMusicDisplay(container, {
      autoResize: false, // керуємо перемальовуванням самі, через ResizeObserver
      backend: 'svg',
      drawTitle: true,
      drawSubtitle: false,
      drawPartNames: false,
      drawMeasureNumbers: true,
      measureNumberInterval: 4,
    })
    osmdRef.current = osmd

    osmd
      .load(musicxml)
      .then(() => {
        if (cancelled) return
        osmd.zoom = zoomRef.current
        osmd.render()
        setRendering(false)
      })
      .catch((err: unknown) => {
        if (cancelled) return
        setFailed(err instanceof Error ? err.message : 'Не вдалося намалювати ноти')
        setRendering(false)
      })

    return () => {
      cancelled = true
      osmdRef.current = null
      container.innerHTML = ''
    }
  }, [musicxml])

  // Масштаб міняємо без повторного парсингу MusicXML.
  useEffect(() => {
    const osmd = osmdRef.current
    if (!osmd || rendering) return
    osmd.zoom = zoom
    osmd.render()
  }, [zoom, rendering])

  // Ширина контейнера змінюється при ресайзі вікна; OSMD сам не стежить,
  // бо autoResize вимкнено. Дебаунс — щоб не перемальовувати на кожен піксель.
  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    let timer: number | undefined
    const observer = new ResizeObserver(() => {
      window.clearTimeout(timer)
      timer = window.setTimeout(() => {
        const osmd = osmdRef.current
        if (osmd?.GraphicSheet) osmd.render()
      }, 250)
    })

    observer.observe(container)
    return () => {
      window.clearTimeout(timer)
      observer.disconnect()
    }
  }, [])

  return (
    <div className="rounded-lg border border-ink/10 bg-white">
      <div className="flex items-center justify-between border-b border-ink/10 px-4 py-2">
        <span className="text-xs uppercase tracking-wide text-muted">Партитура</span>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => setZoom((z) => Math.max(ZOOM_MIN, +(z - ZOOM_STEP).toFixed(2)))}
            disabled={zoom <= ZOOM_MIN}
            className="rounded p-1.5 text-muted transition hover:bg-ink/5 hover:text-ink disabled:opacity-30"
            aria-label="Зменшити"
          >
            <Minus className="h-4 w-4" />
          </button>
          <span className="w-12 text-center font-mono text-xs text-muted">
            {Math.round(zoom * 100)}%
          </span>
          <button
            type="button"
            onClick={() => setZoom((z) => Math.min(ZOOM_MAX, +(z + ZOOM_STEP).toFixed(2)))}
            disabled={zoom >= ZOOM_MAX}
            className="rounded p-1.5 text-muted transition hover:bg-ink/5 hover:text-ink disabled:opacity-30"
            aria-label="Збільшити"
          >
            <Plus className="h-4 w-4" />
          </button>
        </div>
      </div>

      {rendering && (
        <div className="flex items-center justify-center gap-2 py-16 text-muted">
          <Spinner />
          <span className="text-sm">Малюю ноти…</span>
        </div>
      )}

      {failed && (
        <p className="px-4 py-8 text-sm text-accent">
          Ноти не відобразились: {failed}
        </p>
      )}

      <div
        ref={containerRef}
        className="osmd-container overflow-x-auto px-2 pb-4"
        style={{ display: rendering || failed ? 'none' : 'block' }}
      />
    </div>
  )
}